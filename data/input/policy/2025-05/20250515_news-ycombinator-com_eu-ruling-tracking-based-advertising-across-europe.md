---
title: EU ruling: tracking-based advertising [...] across Europe has no legal basis
url: https://news.ycombinator.com/item?id=43992444
published_date: 2025-05-15T00:00:00
collected_date: 2025-05-31T08:02:21.676087
source: News
source_url: https://news.ycombinator.com
description: "EU ruling: tracking-based advertising [...] across Europe has no legal basis ( iccl.ie) 
 81 points by mschuster91 1 hour ago | hide | past | favorite | 31 comments 
 
 
 
 \"Personalized\" advertising isn't good for anyone except the ad networks. It isn't good for consumers whose privacy is..."
language: en
collection_type: policy_landscape
---

# EU ruling: tracking-based advertising [...] across Europe has no legal basis

EU ruling: tracking-based advertising [...] across Europe has no legal basis ( iccl.ie) 
 81 points by mschuster91 1 hour ago | hide | past | favorite | 31 comments 
 
 
 
 "Personalized" advertising isn't good for anyone except the ad networks. It isn't good for consumers whose privacy is...

EU ruling: tracking-based advertising [...] across Europe has no legal basis ( iccl.ie) 
 81 points by mschuster91 1 hour ago | hide | past | favorite | 31 comments

"Personalized" advertising isn't good for anyone except the ad networks. It isn't good for consumers whose privacy is being violated as they are being annoyed with unwanted, irrelevant ads and they get charged higher prices due to the cost of the advertising. It isn't good for companies buying the ads by participating in sham "auctions" with no real insight into or control over the process. They are literally begging to be ripped off. It doesn't have to be this way. "Context sensitive" advertising is more privacy respecting, easier to implement and monitor and can be more cost effective. Example: The fact that I recently shopped for and bought a car is no reason to show me auto ads on a web site devoted to pet supplies. There is a logical disconnect here because context is ignored in favor of "personalization". Those paying for these dumb "personalized" ads are wasting their money and my time and bandwidth because I already made a purchase. I'm not making another one any time soon. By the way, this doesn't really happen to me any more because I now block these "personalized" ad networks. And you should too --- it's the only logical recourse to this stupidity.

I agree. But in the crappy experience topic, it seems to me that this is just bad engineering. If I were to build an algo to show personalized ads, I would definitely account for the likelihood of someone wanting to buy 2 consecutive cars vs a car and maybe some car related products. How was that decision made, because it seems that an entire industry adopted this and called it a day.

&gt; It doesn't have to be this way. "Context sensitive" advertising is more privacy respecting, easier to implement and monitor and can be more cost effective. This is what launched Google's money printing machine: Showing ads matching the current intent (current search) thus solving a current problem.

I actually dislike this sort of advertising even more. Because it pretends to be the solution to your current problem when often it’s not. At least out-of-context ads can be more easily ignored.

The other case for personalised advertising is when a purchase is almost made. I was recently searching for a toy across Etsy, Ali Express, eBay. I didn't buy it. A day later, I saw 'suggested' purchases on Amazon for the same toy. I boycott Amazon, so I don't often visit their website. I normally block (successfully?) almost all of this advertising, so I find it particularly creepy when I receive it.

I believe the main purpose of tracking based advertising is to know your gender, politics and social class to show you the right kind of car and pet supply. This discrimination is quite important and before internet people would self discriminate on those basis and buy different magasines, see different movies, walk different streets and advertisers could target their demographics based on that. Now everybody goes to the same social networks so the tracking is used to provide this discrimination

lol at IAB's choice of headline: "Belgian Market Court Confirms Limited Role of IAB Europe In The TCF" IAB was on the hook for the dreadful cookie "consent" popups that ruined the web (no, it wasn't GDPR that ruined it, it was a very deliberate action by "industry groups" like IAB). The only reason the Market Court annulled the previous decision was on procedural grounds, while agreeing that IAB is responsible, and keeping the 250 000 EUR fine in place. Too bad. I wish Market Court would've burned IAB to the ground, salted the earth and scattered the ashes.

&gt; It applies immediately across Europe. Does anyone know what the consequences are? I have no idea exactly what it is that applies immediately. I would guess that starting today Google and others should stop advertising as they currently do it, it being illegal. I doubt it's that simple, and even if it was, I am sure they will not simply stop. So what happens now?

Tracking has no legal basis, but it's still permitted with consent. The problem with IAB Europe (and other similar ad providers, as well as IAB's customers) is that IAB Europe didn't obtain consent; it tried to hide its tracking by using supposedly non-personal identifiers, which wouldn't necessitate consent, but the court ruled that these identifiers were actually PII. IAB also tried to weasel its way out of its responsibilities, but preventing that seems to have failed. As a result, data collected through IAB about European customers was collected unlawfully, and third parties must delete that data. IAB also can't smuggle consent like this anymore, and needs to pay a fine that was handed down a few years ago. The legal publication can be found here (translated into various languages, though I believe the original may have been Dutch or French as it was the Belgian DPA that started the suit): https://curia.europa.eu/juris/documents.jsf?num=C-604/22 and here https://www.dataprotectionauthority.be/the-market-court-rule... I very much doubt ad companies will actually delete the illegally obtained data, but IAB and other companies in the cyberstalking industry this can be a problem, because they need to actually comply with the law.

&gt;I am sure they will not simply stop. So what happens now? U guess they'll either try to fight it in court somehow or find a loophole to abuse.
Or yknow... just ignore the ruling as long as possible.

I've been working on open source mobile app tracking for advertisers to use (an MMP specifically). Would love to connect with anyone in this thread to discuss it. Specifically, is tracking inside of a single app/property acceptable? So much mobile tracking is added due to a lack of real HTTPS links (in mobile called deferred deep links). To just know whether a user from link X did or did not open the app. Happy to chat with people opposed or pro, feel free to reach out for a longer discussion. https://openattribution.dev

It would be nice to have an opt-in platform where you could select products that you'd like to see ads for. For example, you're looking for a TV or automobile and you want to see deals related to those products.

As I always say, you can’t outlaw being an asshole. But I am curious about what sort of assholery we will see next. Maybe all tracking will become “legitimate interest” (I’m kidding, please don’t actually entrench that garbage any more than it already is).

&gt; the Market Court annulled the BE DPA's decision 21/2022 on procedural grounds. It's a win for advertisers. The court says, the logic holds, but the advertisers will not be fined and will not have to follow the 21/2022 decision.

"Although decision 21/2022 is annulled for procedural reasons, the Market Court endorses the reasoning of the Belgian DPA and confirms the fine of 250,000 euros imposed. However, the Court rejects the BE DPA's conclusion that IAB Europe acts as (joint) data controller for the processing operations that take place entirely within the OpenRTB protocol." https://www.dataprotectionauthority.be/citizen/the-market-co... It's not a pure win.

&gt; The court says, the logic holds, but the advertisers will not be fined. That's common in European jurisdiction. We tend to operate on a "first strike is free" principle, especially in contested / purposefully left unclear legal environments. Only when the case law is clear, it can be shown that a law was intentionally exploited or broken or it's a repeat offender, then we bring the hammer down.

Really? But from what HN told me, any minor violation of the GDPR would be met with a multi-million fine and the GDPR police blasting your doors to arrest everybody /s

The problem is, many people on HN are Americans and assume that the way their jurisdiction works should be an example for everyone else to follow. Our political and legal system prefers self-regulation first, if that doesn't work then regulation will be introduced, the first offenders will get a slap on the wrist to clarify for everyone what the courts' lines on interpreting the law are, and only then the fines follow.

Totally agree. The current ad model feels extractive on all sides. Context-based targeting feels like a more honest middle ground that doesn’t require spying on users.

The "problem" is that oh so many sites have no context. They exist solely to host ads, the content on their pages provide no actual value and is rehashed press-release, direct copies of reporting from Reuters, 10 ten lists written by interns or AI junk. If this works it will be good for everyone, the many issue with today's internet is the perverse incentives to get views or "engagement" so you can sell ad space. The ads are the goal, not the message.

See also the decline of media where they learned very early on that rage generates by far the most clicks and hollowed out their entire fucking industry to sell more ads. Honestly a number of really really significant societal problems have their roots in surveillance capitalism

250k euros for an association of 600+ advertising agencies (IAB) is an exceedingly cheap cost of doing business.

What do you think happens if they are caught again? By then the precedent has been set. Easy decision. Fine them again. And obviously the previous fine didn't work so increase it. Courts have no patience for repeat offenders. Also, it sends a signal to wannabe competitors to this company that there are laws and there are consequences for breaking those. And of course given that these companies have money, there are going to be lawyers paying attention to see if they can get at that money in some way. Germany is almost as bad on that front as California. Lots of enterprising lawyers here. So, one successful court case can trigger many more once the precedent is set.

The fine is nothing, but their core selling point (selling ads without bothering to ask for consent) has been exposed and ruled illegal. The implication is also that data collected for years by those 600+ advertising agencies has been collected illegally, though I doubt deletion of that data will be enforced without a second suit.

Keep in mind that the fines are intended to be progressive. If they don't quit their current practices now that is is clear how the law should be interpreted, the next fine will be substantially larger.

I was quite glad to see this quote in there: &gt; Dr Johnny Ryan said "Today's court's decision shows that the consent system used by Google, Amazon, X, Microsoft, deceives hundreds of millions of Europeans. The tech industry has sought to hide its vast data breach behind sham consent popups. Tech companies turned the GDPR into a daily nuisance rather than a shield for people." I feel this so often gets lost in the conversation where a huge amount of people in communities like this one will loudly point out how annoying consent banners are but never give any thought as to why so many websites feel that just because you want to read a single article on their website that they are now entitled to sell your information often to hundreds and even thousands of different data brokers and that this is now so normalised that it’s almost every bit of content I consume now. The original purpose of the GDPR was clearly to try and put an end to this kind of thing while still leaving cutouts for legitimate purposes with informed consent. I’m so glad to see them come at this from a new angle entirely now to just firmly say that this surveillance capitalism bullshit is illegal and you can’t cookie banner your way out of it as some kind of legal protection. Good, that makes me extremely happy as an EU resident and I wholeheartedly support whatever steps you need to take in order to enforce this. There’s no reason at this point to continue playing nice with US spyware companies masquerading as “data brokers”, let them deal with the mess they made but we don’t need it here.

&gt; The original purpose of the GDPR was clearly to try and put an end to this kind of thing while still leaving cutouts for legitimate purposes with informed consent. Don't forget the "legitimate interest", where somehow 635 ad companies absolutely must have my data to visit a single website...