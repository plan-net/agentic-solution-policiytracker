---
title: Catch Up with What's New for AI in AWS in 2025 -- AWSInsider
url: https://awsinsider.net/Articles/2025/01/09/Catch-Up-with-Whats-New-for-AI-in-AWS-in-2025.aspx
published_date: 2025-05-28T13:21:52.434547
collected_date: 2025-05-28T13:21:52.434610
source: Awsinsider
source_url: https://awsinsider.net
author: By David Ramel01/09/2025
description: [News](https://awsinsider.net/Articles/List/News.aspx)
language: en
---

# Catch Up with What's New for AI in AWS in 2025 -- AWSInsider

*By By David Ramel01/09/2025*

[News](https://awsinsider.net/Articles/List/News.aspx)

[News](https://awsinsider.net/Articles/List/News.aspx)

### Catch Up with What's New for AI in AWS in 2025

- By [David Ramel](https://awsinsider.net/Forms/EmailToAuthor.aspx?AuthorItem={53762E17-6187-46B4-8C04-9DFA282EBB67}&ArticleItem={8371432E-5221-4D99-B7BB-9DD2F644FBEA})
- 01/09/2025

Things slow down in the tech industry over the holiday season, so here's a catch-up of AI news announced by Amazon Web Services (AWS) since Nov. 20, 2024, a Monday when many people started their seasonal vacations, ranging from updates to the Amazon Q dev tool to support for latency optimized models.

**Amazon Q Business Is Now SOC Compliant**

Amazon Q Business, AWS's generative AI-powered assistant, has achieved SOC (System and Organization Controls) compliance as of Dec. 20, 2024. This certification covers SOC 1, 2, and 3, enabling customers to use Amazon Q Business for applications that require SOC compliance.

Key points of this announcement include:

- Amazon Q Business can now be used for SOC-compliant tasks within enterprise systems
- The certification provides insight into AWS's security processes and controls for protecting customer data
- AWS maintains SOC compliance through rigorous third-party audits
- The compliance applies to all AWS Regions where Amazon Q Business is available

This certification enhances Amazon Q Business's capability to handle sensitive enterprise data while maintaining high security and compliance standards. More info [here](https://aws.amazon.com/about-aws/whats-new/2024/12/amazon-q-business-soc-compliant).

**Amazon Bedrock Agents, Flows, and Knowledge Bases Now Support Latency Optimized Models**

These components of Amazon's generative AI platform that enable developers to build sophisticated AI applications now support latency-optimized models through the SDK, as announced on Dec. 23, 2024. This update enhances AI applications built with Amazon Bedrock Tooling by providing faster response times and improved responsiveness.

Key features of this update include:

- Support for latency-optimized versions of Anthropic's Claude 3.5 Haiku model and Meta's Llama 3.1 405B and 70B models
- Reduced latency without compromising accuracy compared to standard models
- Utilization of purpose-built AI chips like AWS Trainium2 and advanced software optimizations
- Immediate integration into existing applications without additional setup or model fine-tuning

This enhancement is particularly beneficial for latency-sensitive applications such as real-time customer service chatbots and interactive coding assistants. The latency-optimized inference support is available in the US East (Ohio) Region via cross-region inference and can be accessed through the Amazon Bedrock SDK using a runtime configuration. More info [here](https://aws.amazon.com/about-aws/whats-new/2024/12/amazon-bedrock-agents-flows-knowledge-optimized-models/).

**AWS Neuron Introduces Support for Trainium2 and NxD Inference**

AWS released Neuron 2.21, introducing several significant updates to its AI infrastructure. The AWS Neuron SDK now supports model training and deployment across Trn1, Trn2, and Inf2 instances, available in various AWS Regions and instance types.

- Support for AWS Trainium2 chips and Amazon EC2 Trn2 instances, including the trn2.48xlarge instance type and Trn2 UltraServer
- Introduction of NxD Inference, a PyTorch-based library integrated with vLLM for simplified deployment of large language and multi-modality models
- Launch of Neuron Profiler 2.0 (beta) with enhanced capabilities and support for distributed workloads
- Support for PyTorch 2.5
- Llama 3.1 405B model inference support on a single trn2.48xlarge instance using NxD Inference
- Updates to Deep Learning Containers and AMIs, with support for new model architectures like Llama 3.2, Llama 3.3, and Mixture-of-Experts (MoE) models
- New inference features including FP8 weight quantization and flash decoding for speculative decoding in Transformers NeuronX
- Additional training examples and features, such as support for HuggingFace Llama 3/3.1 70B on Trn2 instances and DPO support for post-training model alignment

More info [here](https://aws.amazon.com/about-aws/whats-new/2024/12/aws-neuron-trainium2-nxd-inference).

**Llama 3.3 70B Now Available on AWS via Amazon SageMaker JumpStart**

AWS made Meta's Llama 3.3 70B model available through Amazon SageMaker JumpStart as of Dec. 26, 2024. This large language model offers a balance of high performance and computational efficiency, making it suitable for cost-effective AI deployments.

Key features of Llama 3.3 70B include:

- Enhanced attention mechanism for reduced inference costs
- Training on approximately 15 trillion tokens
- Extensive supervised fine-tuning and Reinforcement Learning from Human Feedback (RLHF)
- Comparable output quality to larger Llama versions with fewer resources
- Nearly five times more cost-effective inference operations, according to Meta

Customers can deploy Llama 3.3 70B using either the SageMaker JumpStart user interface or programmatically via the SageMaker Python SDK. SageMaker AI's advanced inference capabilities optimize both performance and cost efficiency for deployments.

The model is available in all AWS Regions where Amazon SageMaker AI is supported. More information is [here](https://aws.amazon.com/about-aws/whats-new/2024/12/llama-3-3-70b-aws-amazon-sagemaker-jumpstart) and in a separate [blog post](https://aws.amazon.com/blogs/machine-learning/llama-3-3-70b-now-available-in-amazon-sagemaker-jumpstart/).

**Amazon Q Developer Is Now Available in Amazon SageMaker Code Editor IDE**

The general availability of Amazon Q Developer in Amazon SageMaker Studio Code Editor was the first AWS AI announcement of 2025, being posted yesterday."SageMaker Studio customers now get generative AI assistance powered by Q Developer right within their Code Editor (Visual Studio Code - Open Source) IDE," AWS said. "With Q Developer, data scientists and ML engineers can access expert guidance on SageMaker features, code generation, and troubleshooting. This allows for more productivity by eliminating the need for tedious online searches and documentation review, and ensuring more time delivering differentiated business value."

Key features and benefits of Amazon Q Developer in SageMaker Studio Code Editor include:

- Expert guidance on SageMaker features
- Code generation tailored to user needs
- In-line code suggestions and conversational assistance
- Step-by-step troubleshooting guidance
- Chat capability for discovering and learning SageMaker features

This integration aims to enhance productivity for data scientists and ML engineers by:

- Eliminating the need for extensive documentation review
- Accelerating the model development lifecycle
- Streamlining code editing, explanation, and documentation processes
- Providing efficient error resolution

Amazon Q Developer is now available in all commercial AWS regions where SageMaker Studio is supported. This feature is accessible to both Amazon Q Developer Free Tier and Pro Tier users, with pricing potentially varying depending on individual service models.

The addition of Amazon Q Developer to SageMaker Studio Code Editor represents a significant step in AWS's efforts to integrate generative AI capabilities into its machine learning development environment, potentially transforming the workflow for data scientists and ML engineers, the company [said](https://aws.amazon.com/about-aws/whats-new/2025/01/amazon-q-developer-sagemaker-code-editor-ide/).

[David Ramel](https://awsinsider.net/cdn-cgi/l/email-protection#d3b7a1b2beb6bf9390bcbda5b6a1b4b6e0e5e3fdb0bcbe) is an editor and writer at Converge 360.

- [![](https://awsinsider.net/Articles/2025/01/09/-/media/ECG/VirtualizationReview/Images/introimages2014/ai_cloud_race.jpg)](https://awsinsider.net/Articles/2025/02/11/AWS-Leads-Cloud-Giants-in-Planned-AI-Spending.aspx)

### [AWS Leads Cloud Giants in Planned AI Spending](https://awsinsider.net/Articles/2025/02/11/AWS-Leads-Cloud-Giants-in-Planned-AI-Spending.aspx)

- [![](https://awsinsider.net/Articles/2025/01/09/-/media/ECG/VirtualizationReview/Images/introimages2014/AI_Choice2.jpg)](https://awsinsider.net/Articles/2025/01/31/DeepSeek-AI-on-AWS-When-to-Use-Bedrock-or-SageMaker.aspx)

### [Brand-New DeepSeek AI on AWS: When to Use Bedrock or SageMaker](https://awsinsider.net/Articles/2025/01/31/DeepSeek-AI-on-AWS-When-to-Use-Bedrock-or-SageMaker.aspx)

- [![](https://awsinsider.net/Articles/2025/01/09/-/media/ECG/VirtualizationReview/Images/introimages2014/GENBlueGlobeandgenerictechimages.jpg)](https://awsinsider.net/Articles/2025/01/27/Connecting-to-an-EC2-Instance-Using-EC2-Instance-Connect-Part-1.aspx)

### [Connecting to an EC2 Instance Using EC2 Instance Connect, Part 1](https://awsinsider.net/Articles/2025/01/27/Connecting-to-an-EC2-Instance-Using-EC2-Instance-Connect-Part-1.aspx)

- [Most Popular Articles](javascript:;)
- [Most Emailed Articles](javascript:;)

### [AWS Leads Cloud Giants in Planned AI Spending](https://awsinsider.net/Articles/2025/02/11/AWS-Leads-Cloud-Giants-in-Planned-AI-Spending.aspx)

### [Brand-New DeepSeek AI on AWS: When to Use Bedrock or SageMaker](https://awsinsider.net/Articles/2025/01/31/DeepSeek-AI-on-AWS-When-to-Use-Bedrock-or-SageMaker.aspx)

### [Catch Up with What's New for AI in AWS in 2025](https://awsinsider.net/Articles/2025/01/09/Catch-Up-with-Whats-New-for-AI-in-AWS-in-2025.aspx)

### [AWS Bedrock AI Shines in 2025 Tech Skills Forecast](https://awsinsider.net/Articles/2025/01/23/AWS-Bedrock-AI-Shines-in-2025-Tech-Skills-Forecast.aspx)

### [Measuring Network Performance Across AWS Regions and Availability Zones](https://awsinsider.net/Articles/2024/12/10/Measuring-Network-Performance-Across-AWS-Regions-and-Availability-Zones.aspx)

Sign up for our newsletter.

Email Address\*\*\*Country\*United States of AmericaAfghanistanÅland IslandsAlbaniaAlgeriaAmerican SamoaAndorraAngolaAnguillaAntarcticaAntigua and BarbudaArgentinaArmeniaArubaAustraliaAzerbaijanAustriaBahamasBahrainBangladeshBarbadosBelarusBelgiumBelizeBeninBermudaBhutanBolivia, Plurinational State ofBonaire, Sint Eustatius and SabaBosnia and HerzegovinaBotswanaBouvet IslandBrazilBritish Indian Ocean TerritoryBrunei DarussalamBulgariaBurkina FasoBurundiCambodiaCameroonCanadaCape Verde (Cabo Verde)Cayman IslandsCuraçaoCentral African RepublicChadChileChinaChristmas IslandCocos (Keeling) IslandsColombiaComorosCongoCongo, the Democratic Republic of theCook IslandsCosta RicaCôte d'IvoireCroatiaCubaCyprusCzech RepublicDenmarkDjiboutiDominicaDominican RepublicEcuadorEgyptEl SalvadorEquatorial GuineaEritreaEstoniaEthiopiaFalkland Islands (Malvinas)Faroe IslandsFijiFinlandFranceFrench GuianaFrench PolynesiaFrench Southern TerritoriesGabonGambiaGeorgiaGermanyGhanaGibraltarGreeceGreenlandGrenadaGuadeloupeGuamGuatemalaGuernseyGuineaGuinea-BissauGuyanaHaitiHeard Island and McDonald IslandsHoly See (Vatican City State)HondurasHong KongHungaryIcelandIndiaIndonesiaIran, Islamic Republic ofIraqIrelandIsle of ManIsraelItalyJamaicaJapanJerseyJordanKazakhstanKenyaKiribatiKorea, Democratic People's Republic ofKorea, Republic ofKuwaitKyrgyzstanLao People's Democratic RepublicLatviaLebanonLesothoLiberiaLibyaLiechtensteinLithuaniaLuxembourgMacaoMacedonia, the former Yugoslav Republic ofMadagascarMalawiMalaysiaMaldivesMaliMaltaMarshall IslandsMartiniqueMauritaniaMauritiusMayotteMexicoMicronesia, Federated States ofMoldova, Republic ofMonacoMongoliaMontenegroMontserratMoroccoMozambiqueMyanmarNamibiaNauruNepalNetherlandsNew CaledoniaNew ZealandNicaraguaNigerNigeriaNiueNorfolk IslandNorthern Mariana IslandsNorwayPakistanOmanPalauPalestinian Territory, OccupiedPanamaParaguayPapua New GuineaPeruPhilippinesPitcairnPolandPortugalPuerto RicoQatarRéunionRomaniaRussian FederationRwandaSaint BarthélemySaint Helena, Ascension and Tristan da CunhaSaint Kitts and NevisSaint LuciaSaint Martin (French part)Saint Pierre and MiquelonSaint Vincent and the GrenadinesSamoaSan MarinoSao Tome and PrincipeSaudi ArabiaSenegalSerbiaSeychellesSierra LeoneSingaporeSint Maarten (Dutch part)SlovakiaSloveniaSolomon IslandsSomaliaSouth AfricaSouth Georgia and the South Sandwich IslandsSouth SudanSpainSri LankaSudanSurinameSvalbard and Jan MayenEswatini (Swaziland)SwedenSwitzerlandSyrian Arab RepublicTaiwan, Province of ChinaTajikistanTanzania, United Republic ofThailandTimor-LesteTogoTokelauTongaTrinidad and TobagoTunisiaTurkeyTurkmenistanTurks and Caicos IslandsTuvaluUgandaUkraineUnited Arab EmiratesUnited KingdomUnited States Minor Outlying IslandsUruguayUzbekistanVanuatuViet NamVenezuela, Bolivarian Republic ofVirgin Islands, BritishVirgin Islands, U.S.Wallis and FutunaWestern SaharaYemenZambiaZimbabwe\*

I agree to this site's [Privacy Policy](https://1105media.com/pages/privacy-policy.aspx)

![](https://awsinsider.net/Captcha.ashx?id=A5C2E91226D9475B8AC3829B9A5696E8)Please type the letters/numbers you see above.

- [Most Popular Articles](javascript:;)
- [Most Emailed Articles](javascript:;)

### [AWS Leads Cloud Giants in Planned AI Spending](https://awsinsider.net/Articles/2025/02/11/AWS-Leads-Cloud-Giants-in-Planned-AI-Spending.aspx)

### [Brand-New DeepSeek AI on AWS: When to Use Bedrock or SageMaker](https://awsinsider.net/Articles/2025/01/31/DeepSeek-AI-on-AWS-When-to-Use-Bedrock-or-SageMaker.aspx)

### [Catch Up with What's New for AI in AWS in 2025](https://awsinsider.net/Articles/2025/01/09/Catch-Up-with-Whats-New-for-AI-in-AWS-in-2025.aspx)

### [AWS Bedrock AI Shines in 2025 Tech Skills Forecast](https://awsinsider.net/Articles/2025/01/23/AWS-Bedrock-AI-Shines-in-2025-Tech-Skills-Forecast.aspx)

### [Measuring Network Performance Across AWS Regions and Availability Zones](https://awsinsider.net/Articles/2024/12/10/Measuring-Network-Performance-Across-AWS-Regions-and-Availability-Zones.aspx)

## Upcoming Training Events

[PowerShell 101: Unleash the Power of Automation](https://techmentorevents.com/events/training-seminars/2025/apr22/home.aspx)

[VSLive! 2-Day Hands-On Training Seminar: Building and Deploying Microservice Applications Using .NET9 and Dapr on Azure Container Apps](https://vslive.com/events/training-seminars/2025/jan28/home.aspx)

[Visual Studio Live! Las Vegas](https://vslive.com/Events/las-vegas-2025/home.aspx)

[Live! 360 2-Day Hands-On Seminar: From Traction to Production: Building Generative AI Applications with Azure AI Studio](https://live360events.com/events/training-seminars/2025/mar25/home.aspx)

[Visual Studio Live! @ Microsoft HQ](https://vslive.com/Events/microsofthq-2025/home.aspx)

[VSLive! 4-Day Hands-On Training Seminar: Hands-on with Blazor](https://vslive.com/events/training-seminars/2025/may5/home.aspx)

[Cybersecurity & Ransomware Live! VirtCon 2025](https://cyberlive360.com/events/virtcon/home.aspx)

[VSLive! 3-Day Hands-On Training Seminar: Master Modern JavaScript: Unlock the Full Potential of Your Code](https://vslive.com/events/training-seminars/2025/june2/home.aspx)

[VSLive! 2-Day Hands-On Training Seminar: Asynchronous and Parallel Programming in C#](https://vslive.com/events/training-seminars/2025/june24/home.aspx)

[VSLive! 4-Day Hands-On Training Seminar: Immersive .NET Full Stack Training: 4-Day Hands-On Experience](https://vslive.com/events/training-seminars/2025/jul15/home.aspx)

[TechMentor @ Microsoft HQ](https://techmentorevents.com/Events/microsofthq-2025/home.aspx)

[Visual Studio Live! San Diego](https://vslive.com/Events/san-diego-2025/home.aspx)

[Live! 360 2-Day Hands-On Seminar: Swimming in the Lakes of Microsoft Fabric and AI – A Hands-on Experience](https://live360events.com/events/training-seminars/2025/sept18/home.aspx)

September 18-19, 2025

[Live! 360 Orlando](https://live360events.com/events/orlando-2025/home.aspx)

[Artificial Intelligence Live! Orlando](https://attendailive.com/ecg/live360events/events/orlando-2025/ailive.aspx)

[Cloud & Containers Live! Orlando](https://cclive360.com/ecg/live360events/events/orlando-2025/cclive.aspx)

[Cybersecurity & Ransomware Live! Orlando](https://cyberlive360.com/ecg/live360events/events/orlando-2025/cyberlive.aspx)

[Data Platform Live! Orlando](https://datalive360.com/ecg/live360events/events/orlando-2025/dataplatform.aspx)

[Visual Studio Live! Orlando](https://vslive.com/ECG/live360events/Events/Orlando-2025/VSLive.aspx)

[TechMentor Orlando](https://techmentorevents.com/ECG/live360events/Events/Orlando-2025/TechMentor.aspx)

[VSLive! 4-Day Hands-On Training Seminar: Immersive .NET Full Stack Training: 4-Day Hands-On Experience](https://vslive.com/events/training-seminars/2025/dec16/home.aspx)

- [Solution Brief \| Building Multi-Cloud Data Resilience With 100% SaaS](https://awsinsider.net/Whitepapers/2025/01/DRUVA-Solution-Brief-Building-MultiCloud-Data-Resilience-With-SaaS.aspx)
- [Datasheet \| Keep Amazon RDS Data Safe with Unmatched Security](https://awsinsider.net/Whitepapers/2025/01/DRUVA-Keep-Amazon-RDS-Data-Safe-with-Unmatched-Security.aspx)
- [Datasheet: AWS Data Protection Sheet](https://awsinsider.net/Whitepapers/2025/01/DRUVA-AWS-Data-Protection-Sheet.aspx)
- [Customer Story: Medallia Lowers Risk by Moving Data Resilience to the Cloud for VMware and AWS Workloads](https://awsinsider.net/Whitepapers/2025/01/DRUVA-Customer-Story-Medallia-Lowers-Risk.aspx)

- [Video \| Next Gen Protection for AWS Workloads](https://awsinsider.net/Webcasts/2025/01/DRUVA-Video-Next-Gen-Protection-for-AWS-Workloads.aspx)
- [Video \| Air-Gapped Backup for Amazon RDS](https://awsinsider.net/Webcasts/2025/01/DRUVA-Video-Air-Gapped-Backup-for-Amazon-RDS.aspx)
- [Scalable Time Series Analytics with InfluxDB on AWS](https://awsinsider.net/Webcasts/2025/02/INFLUX-DATA-Scalable-Time-Series-Analytics-with-InfluxDB-on-AWS.aspx)
- [Webinar: AWS Data Management and Protection Summit: All the Ins, Outs and In-Betweens that Cloud Admins Should Know](https://awsinsider.net/Webcasts/2025/01/DRUVA-Webinar-AWS-Data-Management-and-Protection-Summit.aspx)