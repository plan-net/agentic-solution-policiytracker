---
title: GDPR Website Compliance Checklist for Companies Selling to EU Customers - Feroot Security
url: https://www.feroot.com/blog/gdpr-website-compliance-checklist/
published_date: 2025-11-26T18:00:45
collected_date: 2025-12-01T11:34:23.096595
source: Feroot
source_url: https://www.feroot.com
author: Ivan Tsarynny
description: Blog [Compliance](https://www.feroot.com/blog/?_filter=compliance)
language: en
collection_type: policy_landscape
---

# GDPR Website Compliance Checklist for Companies Selling to EU Customers - Feroot Security

*By Ivan Tsarynny*

Blog [Compliance](https://www.feroot.com/blog/?_filter=compliance)

Blog [Compliance](https://www.feroot.com/blog/?_filter=compliance)

# GDPR Website Compliance Checklist for Companies Selling to EU Customers

[Ivan Tsarynny](https://www.feroot.com/author/ivan-tsarynny/)

As soon as your business starts engaging customers or prospects in the EU, GDPR stops being theoretical. Increased traffic from Europe, localized marketing campaigns, or new regional customers all put your organization squarely within scope.

Yet most teams only discover this when something triggers a review. And when they look, they find the same issues: analytics running without consent, forms collecting personal data without a lawful basis, privacy pages missing [GDPR rights](https://gdpr-info.eu/chapter-3/), and no [DPO](https://www.gdpr.org/regulation/rights-of-the-data-subject.html) or [Article 30](https://gdpr-info.eu/art-30-gdpr) records.

This pattern is common. **GDPR applies to any organization that offers goods or services to people in the EU or monitors the behavior of EU residents, regardless of where the company is headquartered**. A US SaaS provider with German customers is in scope. A Canadian ecommerce brand shipping to France is in scope. An Australian B2B vendor with Dutch clients is in scope. ( [Source](https://www.pwc.lu/en/general-data-protection/docs/pwc-gdpr-territorial-scope.pdf))

## What you will learn in this article

- When GDPR applies to non-EU companies (the EU customer test that most organizations miss)
- The 8 critical GDPR website requirements from cookie consent to processor agreements, and how to implement each one
- Manual implementation vs. AlphaPrivacy AI: effort, timeline, and multi-regulation coverage across GDPR, CCPA, PCI DSS, and 15+ frameworks
- Your 90-day compliance roadmap from audit to ongoing monitoring, with evidence packages that satisfy regulators and enterprise customers

The stakes are real. Regulators can impose fines of up to 20 million euros or 4 percent of global annual turnover for the most serious violations. **In 2023 alone, EU regulators issued about 2.05 billion euros in GDPR fines across hundreds of cases**( [Source](https://europeanbusinessmagazine.com/business/mark-zuckerbergs-companies-fined-2-8-billion-for-wrongful-user-data-processing-gdpr-report-2/)). At the same time, European buyers increasingly ask about GDPR in security questionnaires, contracts, and RFPs. Competitors mention their compliance posture in sales conversations. Privacy is no longer just a legal issue. It is a commercial signal of trust.

The good news is that your website is the best place to start. It is the most visible part of your GDPR obligations and usually the biggest source of personal data collection. You can bring it into compliance in a structured way, without freezing marketing or hiring an army of consultants.

**This guide walks you through a GDPR website compliance checklist for companies selling to EU customers**. It explains when GDPR applies, what your website must do, how to implement requirements manually, and how [automation with **Feroot’s AlphaPrivacy AI** can reduce effort and extend coverage across multiple regulations, not just GDPR.](https://www.feroot.com/alphaprivacy/)

## Does GDPR apply to your company? The EU customer test

**Many non-EU companies assume GDPR does not apply to them because they do not have offices in Europe. The regulation is explicit that this assumption is wrong.**

### The core trigger: Offering goods or services to EU residents

**GDPR Article 3(2)** ( [Source](https://gdpr-info.eu/art-3-gdpr/)) says the regulation applies to controllers or processors outside the EU if their processing is related to either offering goods or services to people in the Union or monitoring their behavior while they are in the Union.

Headquarters location does not matter. What matters is whether you offer products or services to EU residents, whether they pay or not. Or you monitor the online behavior of EU visitors, for example through tracking and profiling.

If your website can accept orders from EU addresses, if your SaaS platform has EU users, or if your marketing campaigns explicitly target European countries, then you are operating under GDPR.

## Clear indicators that GDPR applies to your company

- You sell products or services that ship to EU addresses or are used by EU based customers
- You run marketing campaigns that target EU countries, use EU languages, or show prices in euros
- You process personal data such as names, email addresses, or IP addresses of people in the EU
- You track user behavior of EU visitors with tools like Google Analytics or advertising pixels
- You already have EU customers or users, even if they are a small percentage of revenue
- If any of these are true, you should work on the assumption that GDPR applies.

### Common misconceptions for non EU companies

Several myths keep companies stuck.

One myth is “We are a US or Canadian company, so only US or Canadian law applies.” GDPR has a clear extraterritorial effect. If you process the data of EU residents in the ways described above, you fall under its scope. ( [Source](https://www.pwc.lu/en/general-data-protection/docs/pwc-gdpr-territorial-scope.pdf))

Another myth is “We only have a few EU customers, so regulators will not care.” GDPR does not have a minimum volume threshold. One EU customer is enough to trigger obligations. Regulators may prioritize larger cases, but enterprise buyers and partners do not. They care about your compliance posture even if your EU footprint is still growing.

A third myth is “We will just block EU visitors.” Geo blocking is technically possible, but it is usually bad for SEO, hard to get right, and commercially painful if you already have European customers. It also does not resolve obligations you already have for existing EU data.

### The bottom line test

**Ask one question: Do we have customers, users, or website visitors in the EU whose behavior we track or whose data we collect?** If the answer is yes, then GDPR applies and you should treat your website as an in scope data collection surface.

You do not need to become a European privacy expert overnight. You need a concrete website checklist and a plan for how to implement it within 60 to 90 days.

Here is a simple decision table you can share with executives.

**Table 1. Does GDPR apply to our company?**

| | |
| --- | --- |
| **Situation** | **Does GDPR apply?** |
| We sell products that ship to EU addresses | Yes |
| We have SaaS users with EU email addresses | Yes |
| We run Google Ads or LinkedIn campaigns targeting EU | Yes |
| We have EU website visitors and track their behavior | Yes, if behavior is monitored |
| We are a US company with no EU offices | Still yes, if we have EU customers or tracking |
| We have fewer than 10 EU customers | Yes, there is no minimum threshold |

## The 8 critical GDPR website compliance requirements

Once you know GDPR applies, you can focus your effort on the parts that matter most for your website.

These eight requirements cover what most non EU companies need for a defensible compliance posture online.

### Requirement 1: Lawful basis for data processing

**Under GDPR, you must have a lawful basis for processing personal data**. Website activities usually rely on consent for non essential tracking and on legitimate interests or contracts for core functionality, such as processing an order or operating an account. ( [Source](https://gdpr-info.eu/art-13-gdpr/))

### Requirement 2: Explicit cookie consent

**GDPR, together with the ePrivacy rules, requires consent before placing non essential cookies on EU devices**. That includes analytics cookies, advertising identifiers, and many tags used for remarketing or social media tracking.

For your website, this means non essential cookies should not load until the visitor has actively opted in. Informational banners that say “By continuing to use this site, you agree” are not compliant for EU users. Consent must be a clear, affirmative action, not silent acceptance.

### Requirement 3: Transparent privacy policy

**GDPR Article 13 requires controllers to give data subjects clear information at the time data is collected, including what data is collected, why, who receives it, and how long it is kept.**

Your privacy policy needs to reflect how your website actually works. It should list specific categories of personal data, the purposes for each, the legal basis, the vendors that receive data, and the rights that EU users can exercise. Generic “we may collect information” language is usually not enough.

### Requirement 4: Data subject rights implementation

**GDPR gives individuals rights to access, correct, delete, and restrict the use of their data, among others**. You must handle these data subject rights requests within one month in most cases.

On the website, that usually means:

- A clear way for EU users to contact you about privacy
- Internal processes to locate data in systems like CRM, analytics, and email tools
- Procedures for deletion, export, or restriction when requests come in
- You do not need a complex portal on day one. You do need a reliable workflow and accountability.

### Requirement 5: Data processing records

**GDPR Article 30 requires organizations to maintain records of processing activities that describe what personal data they process, why, who receives it, and for how long they keep it.** ( [Source](https://gdpr-info.eu/art-30-gdpr))

For website compliance, this translates into a structured inventory. You should know:

- Every place you collect personal data on the site
- Every cookie and script that processes that data
- Every third party that receives data from the site

This record is often called a ROPA or Article 30 register.

### Requirement 6: Data Protection Impact Assessments (DPIAs)

**When your processing is likely to result in high risk to individuals, GDPR requires a Data Protection Impact Assessment**. This is a structured risk analysis and mitigation plan.

You should consider a DPIA when your website:

- Uses intensive profiling or automated decision making
- Processes special categories of data, such as health beliefs or political opinions
- Combines data from multiple sources to build detailed behavior profiles

A DPIA does not always mean you must stop the processing. It means you need documented reasoning and safeguards.

### Requirement 7: Security measures

**GDPR Article 32 requires controllers and processors to implement appropriate security of processing**. The regulation highlights encryption, confidentiality, resilience, and regular testing of controls. ( [Source](https://gdpr-info.eu/art-32-gdpr))

For your website, this means at minimum:

- HTTPS everywhere, including landing pages and forms
- Secure handling of form submissions and payment details
- Access controls to admin areas and back end systems
- Documented breach response procedures that include the 72 hour notification window for serious incidents

### Requirement 8: Data processor agreements

Any third party that processes EU personal data on your behalf is a data processor. You must have a Data Processing Agreement (DPA) with each of them that covers their responsibilities and security obligations.

In practice, this includes tools like:

- Analytics platforms
- CRM and marketing automation
- Chat and support widgets
- Form builders and survey tools

Most major vendors now provide standard DPAs that you can sign online. You still need to identify and execute them.

Here is a summary table that connects each requirement to what your website needs.

**Table 2. GDPR website requirements checklist**

| | | |
| --- | --- | --- |
| **GDPR requirement** | **Website implementation focus** | **Documentation you need** |
| Lawful basis | Map each data collection point to a legal basis | Legal basis assessment notes |
| Cookie consent | Block non essential cookies until opt in | Consent logs and CMP configuration records |
| Privacy policy | Clear, specific disclosures about data, purposes, vendors | Updated policy text and review history |
| Data subject rights | Contact channel and internal workflow to fulfill requests | Process documentation and request log |
| Processing records | Inventory of forms, cookies, scripts, and data flows | Article 30 records of processing |
| DPIAs | Risk assessments for high risk tracking or profiling | DPIA documents and decisions |
| Security measures | HTTPS, secure forms, access control, breach plan | Security policies and incident procedures |
| Processor agreements | Signed DPAs with all vendors receiving EU personal data | Executed DPA copies and vendor list |

## Manual approach: implementing GDPR website compliance in house

**If you have technical staff, legal support, and some available time, a manual implementation is entirely achievable**. The work is structured, but it is not magic. It is a series of audits, configuration changes, and documentation updates that you can move through step by step.

**The main tradeoff is time**. Most mid market websites can reach a solid baseline over a few months, then plan for roughly 10 to 15 hours per month of ongoing maintenance as the site and tooling evolve.

### Step 1: Audit your current website data collection

**Start by discovering what your website is actually doing today**. Use browser developer tools and a cookie scanner to see which cookies are being set, which third party scripts load on each page, and where your forms and input flows collect personal data.

As you review, pay attention to patterns. Note which cookies appear across the site, which scripts come from analytics, advertising, or chat providers, and what fields your forms request from users. For each data flow, record the purpose, the data elements involved, and the vendors that receive that data. A simple spreadsheet is usually enough at this stage.

Plan for three to five days for a typical B2B site. Complex ecommerce platforms or applications with many subdomains may require more time, but the goal is the same: a clear picture of what is happening now.

### Step 2: Update your privacy policy

**With your audit results in hand, revise your privacy policy so it reflects reality and aligns with GDPR Article 13 transparency obligations**. Each category of data and each purpose should be described in concrete terms. Explain what personal data you collect through the website, why you collect it and on what legal basis, who receives it, how long you keep it, and how EU users can exercise their rights.

Make sure the vendors you identified in your audit are actually named or clearly described, rather than hidden behind generic phrases like “service providers.” Include a specific contact point for privacy inquiries and, where relevant, contact details for your DPO or privacy lead. Many companies work with GDPR experienced counsel at this stage to ensure the policy language matches both the law and the real data flows you just documented.

### Step 3: Implement cookie consent management

**Next, bring your cookies into line with GDPR requirements by deploying a consent management solution**. Choose a Consent Management Platform that can block non essential cookies until consent is given, support categories such as analytics and advertising, and store consent choices with enough detail to demonstrate compliance later.

Install the CMP script on all pages of your site. Configure it so it recognizes the cookies and scripts you discovered during the audit and assigns them to the correct categories. Then connect those categories to consent states so, for example, analytics scripts only execute when a visitor has actively opted in.

Test this from an EU perspective, ideally using an EU based IP or an emulated environment. Confirm that non essential cookies do not appear until the visitor has accepted the banner and that withdrawing consent stops future tracking.

### Step 4: Establish data subject rights processes

**Design a straightforward process for handling data subject rights**. You do not need a complex portal on day one, but you do need clarity on how requests are received, handled, and closed within the GDPR time limits.

Create a dedicated privacy contact address or form that EU users can find easily. Internally, document how your team will verify the identity of requesters when appropriate, where they will look for that person’s data across your systems, how they will export or delete it when required, and how they will ensure responses go out within one month. Train at least one person in support, legal, and engineering so that if a request arrives in any channel, it is recognized and routed into the same workflow rather than lost in a general inbox.

### Step 5: Execute Data Processing Agreements

**Using the vendor list from your audit, identify every company that processes EU personal data on your behalf**. For each one, locate their Data Processing Agreement or data processing terms and make sure you have formally accepted or signed them.

Most major platforms, such as analytics services, CRM systems, marketing automation, chat tools, and form builders, offer standard GDPR DPAs you can accept online. Keep a central record of which DPAs have been executed, when they were accepted, and which systems they cover. Cross check that your Article 30 records and your privacy policy refer to the same set of processors, so nothing is missed.

### Step 6: Create and maintain documentation

**Finally, bring everything together into a core documentation package**. This should include your Article 30 records for website related processing, your lawful basis assessments for each activity, your consent and CMP configuration details, any DPIAs you have completed for high risk activities, and your security and incident response procedures that involve website data.

From this point on, treat documentation as a living asset. When marketing adds a new tracking tool, when you launch a new form, or when you redesign a major section of the site, update your records. Manual compliance is less about a once off project and more about building a habit: you notice changes, you assess their impact on GDPR obligations, and you capture the results in your documentation so you always know where you stand.

## Automated approach: Using Feroot AlphaPrivacy AI for continuous GDPR compliance

**As your footprint grows, manual monitoring can become difficult to sustain**. Multiple brands, microsites, and campaigns increase the chance that new tracking slips through without review.

This is where automation becomes valuable.

### What Feroot AlphaPrivacy AI solves

[**Feroot AlphaPrivacy AI**](https://www.feroot.com/alphaprivacy/) focuses on the parts of website compliance that are hardest to maintain manually: discovering data collection, detecting new tracking, enforcing consent rules, and keeping documentation current across many regulations.

- Automated discovery of all cookies, scripts, forms, and data flows on your website, updated as your site changes
- Real time detection of new tracking technologies, including tags added by marketing or third parties
- Automatic blocking of non essential cookies and scripts until consent is captured in line with GDPR requirements
- Continuous generation of Article 30 style records, consent logs, and compliance evidence
- Coverage across multiple frameworks, such as GDPR, CCPA, PIPEDA, HIPAA, and PCI DSS, instead of a single regulation

Instead of relying on periodic manual audits, you get a continuous live map of your website’s personal data footprint and controls that adapt as that footprint changes.

### How implementation works in practice

**Implementation usually follows a straightforward pattern.**

**You deploy a single script across your site. Feroot AlphaPrivacy AI then crawls and observes your pages, identifies all cookies and scripts, and classifies them by purpose and regulatory impact**. Within a day or two, you have a complete picture of where personal data is collected, which tools are involved, and how this maps to GDPR and other frameworks.

You then configure high level policies. For example, non essential cookies blocked until opt in for EU users, analytics allowed with consent, advertising tags allowed only in certain jurisdictions. AlphaPrivacy AI applies these policies in real time and updates them when new elements appear.

The system continuously updates your documentation. If a new script is added, it appears in your inventory, is evaluated against the rules, and either allowed under the correct conditions or blocked until configured.

### What this means for EU customer compliance

**For companies with growing EU revenue or mixed regulatory obligations, this approach does more than save time**. It helps ensure you do not accidentally fall out of compliance as marketing experiments, new tools are adopted, or additional regions come online.

- A website that behaves correctly for EU visitors in terms of consent and tracking
- Documentation that can be handed to regulators or enterprise customers without weeks of manual compilation
- A single system that recognizes that EU customers are not your only compliance concern

**Table 3. Manual implementation vs Feroot AlphaPrivacy AI**

| | | |
| --- | --- | --- |
| **Aspect** | **Manual implementation** | **Feroot AlphaPrivacy AI** |
| Initial data discovery | 3 to 5 days per site, recurring as site changes | 24 to 48 hours, automatic and continuous |
| Cookie consent enforcement | CMP configuration and ongoing script mapping | Automatic enforcement tied to policy |
| New tracking detection | Monthly or quarterly audits | Real time detection and classification |
| Multi regulation coverage | Separate projects for GDPR, CCPA, PCI, etc | Integrated coverage for 18 plus frameworks |
| Documentation maintenance | Manual updates to records and logs | Automatically generated and updated |
| Ongoing effort | 10 to 15 hours per month per active site | Minimal oversight after initial configuration |

The goal is not to replace your judgment. It is to give you better visibility and stronger guardrails so that your decisions are consistently enforced, even when your marketing and product teams are moving quickly.

## Your 90 day GDPR website compliance roadmap

Whether you choose manual implementation, automation with AlphaPrivacy AI, or a hybrid approach, it helps to think in terms of a 90 day project.

- **Days 1 to 30: Assessment and quick wins**. Audit your website data collection. Identify all cookies, scripts, and forms. Update your privacy policy to include GDPR specific information about data types, purposes, and rights. Deploy at least a basic consent banner for EU visitors so that you can show good faith progress while you refine full blocking rules.
- **Days 31 to 60: Implementation and documentation**. Configure a CMP or AlphaPrivacy AI to block non essential cookies until consent. Execute DPAs with key vendors like analytics and CRM providers. Establish your data subject rights process and create Article 30 records for your website related processing. Ensure your security measures are documented and applied consistently.
- **Days 61 to 90: Validation and ongoing processes**. Test that non essential cookies really do not load before consent for EU users. Run a mock data subject request to prove you can respond within the time limit. Train marketing and web teams on the new processes for adding tools and campaigns. Set a recurring review cadence, even if you are using automation, so leadership stays engaged.

By day 90, most companies should have:

- A website that handles EU cookies and tracking in a compliant way
- An updated, transparent privacy policy aligned with GDPR Articles 13 and 30
- A working process for handling data subject rights requests
- Executed DPAs with all core vendors that receive EU personal data
- Documentation that can be shared with auditors or enterprise buyers on request

From there, compliance becomes an ongoing practice, not a project. Websites change. Tools change. Regulations evolve. The difference is that you now have a structure and, if you choose automation, a set of safeguards that change with you.

### Do we really need to comply with GDPR if we are based in the US, Canada, or Australia?

Yes, if you have EU customers or track the behavior of EU visitors in a structured way. Territorial scope is based on where the data subjects are, not where your headquarters is.

### What counts as offering goods or services to EU residents?

If you accept orders from EU addresses, let EU users sign up for your SaaS, market directly to EU countries, or price in euros, regulators are likely to view that as offering goods or services.

### Can we just block EU visitors instead?

You can, but it is often more painful than compliance. Geo blocking can break SEO strategies, complicate operations, and frustrate EU prospects who want to buy from you. It also does nothing to resolve obligations related to EU customer data you already hold.

### Do we need a Data Protection Officer?

GDPR requires a dedicated DPO only in specific situations, such as large scale systematic monitoring or processing of special categories of data. Many companies with EU customers do not meet those thresholds. You still need someone accountable for privacy, but that can be part of an existing role.

### What are the real chances of a large GDPR fine?

The maximum fine levels are reserved for severe or persistent violations, but smaller fines are common and reputational damage often matters more. With over 2 billion euros in fines in 2023, enforcement is not theoretical.

Realizing you have been selling to EU customers without a structured GDPR program can feel uncomfortable. It is easy to imagine regulators, customers, and competitors using that gap against you.

What we have seen in practice is more encouraging. Website compliance is a tractable problem. With a clear checklist and a 90 day plan, you can move from uncertainty to a position where your website, your privacy policy, and your internal processes support your growth in Europe instead of holding it back.

**Manual implementation is a fit for teams with time and in house expertise.** [**Automated monitoring with AlphaPrivacy AI**](https://www.feroot.com/alphaprivacy/) **is a fit when your site is complex, your marketing is active, or you need to align website behavior with many regulations at once**.

In both cases, the outcome is the same: your website handles EU personal data in a way that meets GDPR expectations, gives buyers confidence, and keeps your sales team in the conversation when privacy questions arise.

[Australian Privacy Principles\
\
Client-Side Security\
\
Compliance\
\
**OAIC Compliance Guide: Australian Privacy Principles (APPs) for Web and Mobile** \
\
The Office of the Australian Information Commissioner’s (OAIC) 2025 approach places more weight on how systems behave than how policies read. It…\
\
November 25, 2025](https://www.feroot.com/blog/oaic-apps-compliance-web-mobile-implementation/)[Compliance\
\
**CBUAE 3057 Compliance: Securing the Client Side** \
\
The Central Bank of the UAE’s Notice No. CBUAE/FCMCP/2025/3057 has set a critical deadline of March 31, 2026, for Licensed Financial Institutions…\
\
November 20, 2025](https://www.feroot.com/blog/achieve-cbuae-3057-compliance/)[Comparisons\
\
Compliance\
\
**Secureframe vs Feroot PaymentGuard AI for PCI DSS 4.0.1 Compliance** \
\
PCI DSS 4.0.1 expects two things at once: a well run compliance program and real visibility into what happens on live payment…\
\
November 18, 2025](https://www.feroot.com/blog/secureframe-vs-feroot-paymentguard/)