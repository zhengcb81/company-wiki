"""Offline prose language observations; real saved failure and generic counterexamples."""
from dataclasses import FrozenInstanceError
import importlib
import hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
import threading

import pytest

from company_wiki.source_catalog.narrative_evidence import SummaryClaim
from company_wiki.source_contract.evidence_span import EvidenceCoordinates, EvidenceSpan


@pytest.fixture
def observer():
    return importlib.import_module("company_wiki.automation.narrative_output_language")


@pytest.fixture(autouse=True)
def preserve_production_config():
    root = Path(__file__).resolve().parents[2]
    protected = {p: (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_size, p.stat().st_mtime_ns)
                 for p in (root / "config.yaml", root / "config/source_catalog.yaml")}
    yield
    assert all((hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_size, p.stat().st_mtime_ns) == before
               for p, before in protected.items())


def span(text, index=1):
    return EvidenceSpan.create(source_id="urn:company-wiki:source:sha256:" + "1" * 64,
        coordinates=EvidenceCoordinates(page_number=index, paragraph_index=index), raw_text=text,
        structured_value={}, parser_name="language-fixture", parser_version="1.0.0",
        parse_status="parsed", quality_flags=())


def claim(text, spans, index=1):
    return SummaryClaim(f"c{index}", text, tuple(s.span_id for s in spans), "company_statement", "actual")


def observe(observer, texts, sources):
    spans = tuple(span(text, index) for index, text in enumerate(sources, start=1))
    claims = tuple(claim(text, spans, index) for index, text in enumerate(texts, start=1))
    return observer.observe_summary_language(claims, evidence_spans=spans)


_PROSE = {'synthetic-en-1': 'The new plasma reactor completed customer validation this quarter and received repeat orders. Shipments increased as the installation team reduced the time needed to qualify each production line.', 'synthetic-en-2': 'Monthly output reached eighty thousand eight-inch equivalent wafers. Utilization increased by six percentage points, while the product mix shifted toward automotive and industrial applications.', 'synthetic-en-3': 'Research spending increased in absolute terms, but its share of sales declined because customer shipments grew faster. The engineering team continued work on the next generation of deposition tools.', 'synthetic-en-4': 'Remaining performance obligations rose as enterprise customers renewed multiyear contracts. Roughly one third is expected to become revenue during the next twelve months, subject to delivery and acceptance.', 'synthetic-en-5': 'The retail network added forty stores in overseas markets. Inventory turnover days increased from ninety to one hundred and ten as new products reached distribution partners later than planned.', 'synthetic-en-6': 'Cloud demand continued to grow, but access to electrical power and suitable sites constrained capacity expansion. Management expects the next datacenter phase to begin operating in the second half of next year.', 'synthetic-es-1': 'El nuevo reactor de plasma completó la validación con los clientes y recibió pedidos repetidos durante el trimestre. Los envíos aumentaron gracias a una reducción del tiempo de instalación en cada línea de producción.', 'synthetic-es-2': 'La capacidad mensual alcanzó ochenta mil obleas equivalentes de ocho pulgadas. La utilización subió seis puntos porcentuales y la mezcla de productos se orientó hacia aplicaciones de automoción e industriales.', 'synthetic-es-3': 'El gasto en investigación creció en términos absolutos, pero su proporción sobre las ventas disminuyó porque los envíos aumentaron más rápidamente. El equipo continúa desarrollando herramientas de deposición de nueva generación.', 'synthetic-es-4': 'Las obligaciones de desempeño pendientes aumentaron con la renovación de contratos empresariales plurianuales. Aproximadamente un tercio se reconocerá como ingresos durante los próximos doce meses, sujeto a entrega y aceptación.', 'synthetic-es-5': 'La red comercial añadió cuarenta tiendas en mercados internacionales. Los días de rotación del inventario subieron de noventa a ciento diez porque los nuevos productos llegaron a los distribuidores más tarde de lo previsto.', 'synthetic-es-6': 'La demanda de servicios en la nube siguió creciendo, pero la disponibilidad de electricidad y terrenos adecuados limitó la expansión. La siguiente fase del centro de datos entraría en funcionamiento en el segundo semestre del próximo año.', 'synthetic-fr-1': "Le nouveau réacteur à plasma a terminé sa validation auprès des clients et reçu des commandes supplémentaires pendant le trimestre. Les livraisons ont augmenté grâce à la réduction du délai d'installation sur chaque ligne de production.", 'synthetic-fr-2': "La capacité mensuelle a atteint quatre-vingt mille plaques équivalentes de huit pouces. Le taux d'utilisation a progressé de six points de pourcentage et le portefeuille s'est orienté vers l'automobile et les applications industrielles.", 'synthetic-fr-3': "Les dépenses de recherche ont augmenté en valeur absolue, mais leur poids dans le chiffre d'affaires a diminué parce que les livraisons ont progressé plus rapidement. L'équipe développe la prochaine génération d'équipements de dépôt.", 'synthetic-fr-4': "Les obligations de prestation restantes ont augmenté grâce au renouvellement de contrats pluriannuels. Environ un tiers devrait être comptabilisé en chiffre d'affaires au cours des douze prochains mois, sous réserve de livraison et d'acceptation.", 'synthetic-fr-5': "Le réseau de distribution a ouvert quarante magasins à l'étranger. La durée de rotation des stocks est passée de quatre-vingt-dix à cent dix jours, les nouveaux produits ayant été livrés aux distributeurs plus tard que prévu.", 'synthetic-fr-6': "La demande de services cloud continue de croître, mais l'accès à l'électricité et aux terrains disponibles limite les capacités. La prochaine phase du centre de données devrait démarrer au second semestre de l'année prochaine.", 'synthetic-zh-1': '新一代等离子体刻蚀设备本季度完成客户验证，并获得重复订单。安装团队缩短了生产线的调试周期，因此设备交付量上升，但公司没有披露新增订单的具体金额。', 'synthetic-zh-2': '公司的月产能达到折合八英寸标准逻辑晶圆八万片，产能利用率同比提高六个百分点。产品组合向汽车和工业应用倾斜，不能把八英寸等效产能当成十二英寸实物片数。', 'synthetic-zh-3': '研发投入绝对金额增加，但研发费用占营业收入的比重下降，原因是客户出货量增长更快。工程团队仍在开发下一代薄膜沉积设备，尚未宣布该设备进入量产阶段。', 'synthetic-zh-4': '企业客户续签多年合同带动剩余履约义务增加，约三分之一预计在未来十二个月确认收入，但仍取决于交付和客户验收。尚未确认的订单不能直接当成本年度收入。', 'synthetic-zh-5': '公司在海外新增四十家门店，存货周转天数从九十天升至一百一十天。新产品到达渠道的时间晚于计划，因此周转变慢，不能把天数增加解释为库存效率改善。', 'synthetic-zh-6': '公司完成 NanoWave X7 与 OrionPhoton 系列设备验证，GaN、SiC 和 Al2O3 工艺表现稳定，并在客户产线上获得重复订单。下一代型号仍在研发，预计明年交付验证，尚未量产。', 'en-names': 'The company signed a distribution agreement with Société Lumière and Ingeniería del Norte. The partners will market the new sensors in France and Spain; these names do not change the language of this English description.', 'en-brand': 'NanoWave X7 supports GaN, SiC and Al2O3 processing. Customers validated the platform in production and ordered additional chambers during the quarter. Revenue recognition remains subject to installation and acceptance.', 'en-quote': 'Management described the pilot as ‘une étape importante’ in the project. The French quotation is a short original phrase inside an otherwise English account of the current validation stage and customer response.', 'zh-brand': '本季度 Atlas Cloud 与 AlpineDesk 平台新增企业客户，NanoWave X7 设备获得重复订单。Société Lumière 是法国合作伙伴的专有名称，品牌、型号与化学式不表示这段中文被翻译成英文。', 'real-single-stage-paraphrase': 'The datacenters depend on permitted buildable land, predictable energy, network supplies, servers and GPUs.'}
_SAVED_MM_CLAIMS = [('Reportes en tres segmentos (Productividad y Procesos de Negocio; Nube Inteligente; Computación Más Personal); en agosto 2024 se anunció reagrupar los componentes comerciales de Microsoft 365 en Productividad y Procesos de Negocio, aplicable desde el año fiscal 2025 con recast de períodos previos.', ['e5', 'e7', 'e57', 'e86', 'e92']), ('Microsoft 365 Commercial integra Office, Windows, Microsoft 365 Copilot y Enterprise Mobility + Security como plataforma de productividad potenciada por IA, cuyo crecimiento depende de ampliar usuarios (trabajadores de primera línea, PyMEs, mercados de crecimiento) y de añadir herramientas/escenarios agenticos; los asientos crecieron 6% en el período, con crecimiento cloud de 15% y de productos de 7%.', ['e5', 'e10', 'e69']), ('Microsoft 365 Consumer cloud creció 11% con 89.0 millones de suscriptores (+8%) en el período, apoyado en un aumento de precio anunciado en enero de 2025 y mayor revenue por usuario.', ['e68', 'e69', 'e70']), ('Server products y servicios en la nube crecieron 23% impulsados por Azure y otros servicios en la nube (34%); los server products cayeron 3% por menor compra transaccional y migración a la nube.', ['e71', 'e72', 'e17']), ('Azure AI ofrece capacidad de supercómputo a escala con un portafolio en rápida expansión (modelos más recientes) y silicio propio, complementado con alianzas con fabricantes de chips; Azure AI Foundry es la plataforma unificada para diseñar, personalizar y gestionar aplicaciones y agentes de IA.', ['e16', 'e18']), ('Enterprise and partner services crecieron 2% por aumento en Enterprise Support Services, parcialmente compensado por una caída en Industry Solutions; el portafolio incluye Enterprise Support Services, Industry Solutions, Nuance professional services, Microsoft Partner Network y Learning Experience.', ['e71', 'e73', 'e15', 'e20', 'e37']), ('Surface (incluidos los Copilot+ PCs) y accesorios de PC componen el negocio de Devices, cuyo crecimiento depende del total de envíos de PC, la atracción de nuevos clientes, el roadmap y la entrada en nuevas categorías.', ['e22', 'e26']), ('El negocio de Gaming creció 9%: Xbox content and services +16% impulsado por la adquisición de Activision Blizzard y Xbox Game Pass, mientras Xbox hardware cayó 25% por menor volumen de consolas vendidas.', ['e27', 'e28', 'e74']), ('Search and news advertising creció 13% en el período; excluyendo traffic acquisition costs el crecimiento fue 20% por mayor volumen y mayor revenue por búsqueda.', ['e71', 'e75']), ('La compañía planea mantener inversiones significativas en investigación y desarrollo en un amplio rango de productos, coordinando la I+D entre segmentos y apoyando la investigación fundamental.', ['e30', 'e35']), ('Los datacenters se alinean con la demanda evolutiva de servicios de IA y dependen de disponibilidad de suelo edificable, energía y redes predecibles, así como de servidores y GPUs; las operaciones pueden verse afectadas por escasez de componentes calificados, capacidad de proveedores y cambios en la cadena de suministro.', ['e30', 'e31', 'e33', 'e44']), ('Activision Blizzard fue adquirida el 13 de octubre de 2023 por US$75.4 mil millones (principalmente en efectivo); los resultados financieros se consolidan desde la fecha de adquisición dentro del segmento More Personal Computing.', ['e89', 'e90']), ('Con el cambio de segmentos en el Q1 del año fiscal 2025 también se modificaron las reporting units; el goodwill se reasignó con enfoque de valor relativo tras confirmar ausencia de impairment.', ['e91', 'e92']), ('Al 30 de junio de 2025, la remaining performance obligation era de US$375 mil millones (US$368 mil millones en la porción comercial), con aproximadamente 40% esperado a reconocer en los siguientes 12 meses.', ['e93', 'e94']), ('El CODM (también CEO) revisa información financiera segmentada y utiliza operating income como medida principal de rentabilidad para asignar recursos y evaluar desempeño en tres segmentos.', ['e95', 'e96']), ('El panorama comercial exterior está sujeto a aranceles de EE. UU., controles de exportación (incluida la posibilidad de reemplazar la AI Diffusion Rule recientemente rescindida) y sanciones por conflictos en Ucrania e Israel-Hamas; estas medidas pueden afectar la continuidad de productos, incrementar costos operativos y acelerar iniciativas de soberanía entre socios y clientes internacionales.', ['e46']), ('La legislación Pillar Two de la OCDE aplica a Microsoft desde el año fiscal 2025 con una tasa mínima global del 15%; la compañía estima actualmente un impacto no material en sus estados financieros consolidados y continúa monitoreando.', ['e76', 'e78']), ('La compañía está invirtiendo en IA en toda la empresa e integrando capacidades generativas en ofertas comerciales y de consumo, afrontando costos significativos de desarrollo, operación, infraestructura y plataformas para atender a los clientes en un mercado altamente competitivo y de rápida evolución.', ['e36', 'e38']), ('Competidores modifican y distribuyen software de código abierto con poco o ningún costo, desarrollan modelos de IA abiertos y monetizan vía publicidad o servicios integrados; algunos productos de código abierto imitan funciones de la oferta de Microsoft.', ['e36', 'e39']), ('¿Cuál es el desglose cuantitativo entre infraestructura cloud/IA y dispositivos en el aumento previsto de costos operativos y la potencial presión sobre márgenes operativos?', ['e53'])]
_SAVED_MM_SPANS = {'e5': 'Item 1', 'e7': 'In August 2024, we announced changes to the composition of our segments. These changes align our segments with how we currently manage our business, most notably bringing the commercial components of Microsoft 365 together in the Productivity and Business Processes segment. Beginning in fiscal year 2025, the information that our chief operating decision maker is regularly provided and reviews for purposes of allocating resources and assessing performance reflects these segment changes.', 'e10': 'Microsoft 365 Commercial is an AI-powered business and productivity solutions platform that brings together Office, Windows, Microsoft 365 Copilot, and Enterprise Mobility + Security to help organizations empower their employees. Growth depends on our ability to reach new users in new markets such as frontline workers, small and medium businesses, and growth markets, as well as add AI-enabled tools, features, and agentic scenarios to our core product and service offerings across communication, collaboration, analytics, security, compliance, and other AI business productivity categories. Microsoft 365 Commercial revenue is mainly affected by a combination of continued installed base growth and average revenue per user expansion, as well as the continued shift from Office licensed on-premises to Microsoft 365.', 'e15': 'Enterprise and partner services, including Enterprise Support Services, Industry Solutions, Nuance professional services, Microsoft Partner Network, and Learning Experience.', 'e16': 'Item 1', 'e17': 'Azure is a comprehensive set of cloud services that offer developers, IT professionals, and enterprises freedom to build, deploy, and manage applications on any platform or device. Customers can use Azure through our global network of datacenters for computing, networking, storage, mobile and web application services, AI, Internet of Things, cognitive services, and machine learning. Azure enables customers to devote more resources to development and use of applications that benefit their organizations, rather than managing on-premises hardware and software. Azure revenue is mainly affected by infrastructure-as-a-service and platform-as-a-service consumption-based services.', 'e18': 'Azure AI offerings provide a competitive advantage as companies seek ways to optimize and scale their business with AI. We offer supercomputing power for AI at scale to run large workloads, complemented by our rapidly expanding portfolio of AI cloud services (including the latest models) and hardware, which includes custom-built silicon and strong partnerships with chip manufacturers. Azure AI Foundry is a unified platform for developers to design, customize, and manage AI applications and agents.', 'e20': 'Enterprise and Partner Services', 'e22': 'Item 1', 'e26': 'We design and sell devices, such as Surface (including Copilot+ PCs) and PC accessories. Our devices are designed to enable people and organizations to connect to the people and content that matter most using Windows and integrated Microsoft products and services. Surface is designed to help organizations, students, and consumers be more productive. Growth in Devices is dependent on total PC shipments, the ability to attract new customers, our product roadmap, and expanding into new categories.', 'e27': 'Item 1', 'e28': 'Xbox enables people to connect and share online gaming experiences that are accessible on Xbox consoles, Windows-enabled devices, and other devices. Xbox is designed to benefit users by providing access to a network of certified applications and services and to benefit our developer and partner ecosystems by providing access to a large customer base. Xbox revenue is mainly affected by subscriptions and sales of first- and third-party content, as well as advertising. Growth of our Gaming business is determined by the overall active user base through Xbox enabled content, availability of games, providing exclusive game content that gamers seek, the computational power and reliability of the devices used to access our content and services, and the ability to create new experiences.', 'e30': 'Item 1', 'e31': 'In addition to our operations centers, we also operate datacenters throughout each of these regions. We continue to align our datacenter locations and server capacity to meet the evolving needs of our customers, particularly given the growing demand for AI services. Our datacenters depend on the availability of permitted and buildable land, predictable energy, networking supplies, and servers, including graphics processing units (“GPUs”) and other components.', 'e33': 'There are few qualified suppliers for certain components of our servers and devices. Extended or unforeseen disruptions at these suppliers could impact our ability to operate our datacenters and manufacture devices on time to meet consumer demand.', 'e35': 'We plan to continue to make significant investments in a broad range of product research and development activities, and as appropriate, we will coordinate our research and development across operating segments and leverage the results across the company. This includes continuing to support fundamental research, which provides us with a unique perspective on future trends and contributes to our innovation.', 'e36': 'Item 1A', 'e37': 'A material part of our business involves cloud-based services available across the spectrum of computing devices. We and our competitors continue to devote significant resources to developing and deploying cloud-based strategies and services for consumers and business customers, and pricing and delivery models are evolving.', 'e38': 'We are investing in artificial intelligence (“AI”) across the entire company and infusing generative AI capabilities into our consumer and commercial offerings. AI technology and services are a highly competitive and rapidly evolving market, and new competitors continue to enter the market. We will bear significant development and operational costs to build and support the AI models, services, platforms, and infrastructure necessary to meet the needs of our customers. To compete effectively we must also be responsive to technological change, new and potential regulatory developments, and public scrutiny.', 'e39': 'Some companies compete with us by modifying and then distributing open source software at little or no cost to end users, developing, making available, or using AI models that are open, and earning revenue on advertising or integrated products and services. These firms do not bear the full costs of research and development for the open source products. Some open source products mimic the features and functionality of our products.', 'e44': 'We may have excessive outages, data losses, and disruptions of our online services if we fail to maintain an adequate operations infrastructure. Our increasing user traffic, growth in services, and the complexity of our products and services demand more computing power. We spend substantial amounts to build, purchase, or lease datacenters and equipment and to upgrade our technology and network infrastructure to handle more traffic on our websites and in our datacenters. Our datacenters depend on the availability of permitted and buildable land, predictable energy, networking supplies, and servers, including graphics processing units and other components. The cost or availability of these dependencies could be adversely affected by a variety of factors, including the transition to a clean energy economy, local and regional environmental regulations, and geopolitical disruptions. These demands continue to increase as we introduce new products and services and support the growth and the augmentation of existing services, including through the incorporation of AI features and/or functionality. We are rapidly growing our business of providing a platform and back-end hosting for services provided by third parties to their end users. Maintaining, securing, and expanding this infrastructure is expensive and complex, and requires development of principles for datacenter builds in geographies with higher safety and reliability risks. It requires that we maintain an Internet connectivity infrastructure and storage and compute capacity that is robust and reliable within competitive and regulatory constraints that continue to evolve. Inefficiencies or operational failures, including temporary or permanent loss of customer data, outages, insufficient Internet connectivity, insufficient or unavailable power or water supply, or inadequate storage and compute capacity could diminish the quality of our products, services, and user experience, resulting in contractual liability, claims by customers and other third parties, regulatory actions, damage to our reputation, and loss of current and potential users, subscribers, and advertisers, each of which could adversely affect our business, operations, financial condition, and results of operations.', 'e46': 'Trade: Increasing trade laws, policies, sanctions, and other regulatory requirements also affect our operations in and outside the U.S. relating to trade and investment. Economic sanctions in the U.S., the EU, and other countries prohibit most business with restricted entities or countries. U.S. export controls restrict Microsoft from offering many of its products and services to, or making investments in, certain entities in specified countries. U.S. import controls restrict us from integrating certain information and communication technologies into our supply chain and allow for government review of transactions involving information and communications technology from countries determined to be foreign adversaries. Supply chain regulations may impact the availability of goods or result in additional regulatory scrutiny. Restrictions on data flows and outbound investment and customer sensitivities may limit our ability to leverage parts of our global engineering footprint to provide services in certain jurisdictions. Increased geopolitical instabilities and changing U.S. Administration priorities create an unpredictable trade landscape. U.S. tariff and shifting AI export controls policies, like the AI Diffusion Rule, could increase operational costs, create uncertainty in the continuity of our products, and accelerate sovereignty initiatives among international partners and customers. The volatility of U.S. tariffs has triggered economic uncertainty and could impact cloud and devices supply chain cost competitiveness. The potential replacement of the recently rescinded AI Diffusion Rule and other potential AI-related rulemakings could adversely affect Microsoft’s business, strategy, and operations. Periods of intense diplomatic or armed conflict like the ongoing conflict in Ukraine and the Israel-Hamas conflict could result in (1) new and rapidly evolving sanctions and trade restrictions, which may impair trade with sanctioned individuals and countries, and (2) negative impacts to regional trade ecosystems among our customers, partners, and us.', 'e53': 'The investments we are making in cloud and AI infrastructure and devices will continue to increase our operating costs and may decrease our operating margins. We continue to identify and evaluate opportunities to expand our datacenter locations and increase our server capacity to meet the evolving needs of our customers, particularly given the growing demand for AI services. Our datacenters depend on the availability of permitted and buildable land, predictable energy, networking supplies, and servers, including graphics processing units (“GPUs”) and other components. Our devices are primarily manufactured by third-party contract manufacturers. For the majority of our products, we have the ability to use other manufacturers if a current vendor becomes unavailable or unable to meet our requirements. However, some of our products contain certain components for which there are very few qualified suppliers. Extended disruptions at these suppliers could impact our ability to manufacture devices on time to meet consumer demand.', 'e57': 'In August 2024, we announced changes to the composition of our segments. These changes align our segments with how we currently manage our business, most notably bringing the commercial components of Microsoft 365 together in the Productivity and Business Processes segment. Beginning in fiscal year 2025, the information that our chief operating decision maker is regularly provided and reviews for purposes of allocating resources and assessing performance reflects these segment changes. Prior period segment information has been recast to conform to the way we internally manage and monitor our business during fiscal year 2025.', 'e68': 'Item 7', 'e69': 'Microsoft 365 Commercial products and cloud services revenue increased $10.8 billion or 14%. Microsoft 365 Commercial cloud revenue grew 15% with Microsoft 365 Commercial seat growth of 6% driven by small and medium businesses and frontline worker offerings, as well as growth in revenue per user. Microsoft 365 Commercial products revenue grew 7% driven by the Windows Commercial on-premises components of Microsoft 365 suite sales and an increase in Office transactional purchasing with the launch of Office 2024.', 'e70': 'Microsoft 365 Consumer products and cloud services revenue increased $756 million or 11%. Microsoft 365 Consumer cloud revenue grew 11% driven by Microsoft 365 Consumer subscriber growth of 8% to 89.0 million, as well as growth in revenue per user from the price increase announced in January 2025.', 'e71': 'Item 7', 'e72': 'Server products and cloud services revenue increased $18.6 billion or 23% driven by Azure and other cloud services. Azure and other cloud services revenue grew 34% driven by demand for our portfolio of services. Server products revenue decreased 3% driven by a decrease in transactional purchasing with continued customer shift to cloud offerings.', 'e73': 'Enterprise and partner services revenue increased $166 million or 2% driven by growth in Enterprise Support Services, offset in part by a decline in Industry Solutions.', 'e74': 'Gaming revenue increased $2.0 billion or 9% driven by growth in Xbox content and services, offset in part by a decline in Xbox hardware. Xbox content and services revenue increased 16% driven by the impact of the Activision Blizzard acquisition and Xbox Game Pass. Xbox hardware revenue decreased 25% driven by lower volume of consoles sold.', 'e75': 'Search and news advertising revenue increased $1.6 billion or 13%. Search and news advertising revenue excluding traffic acquisition costs increased 20% driven by higher search volume and higher revenue per search.', 'e76': 'Item 7', 'e78': 'The Organisation for Economic Co-operation and Development (“OECD”) published its model rules “Tax Challenges Arising From the Digitalisation of the Economy - Global Anti-Base Erosion Model Rules (Pillar Two)” which established a global minimum corporate tax rate of 15% for certain multinational enterprises. Many countries have implemented or are in the process of implementing the Pillar Two legislation, which applies to Microsoft beginning in fiscal year 2025. While we do not currently estimate a material impact to our consolidated financial statements, we continue to monitor the impact as countries implement legislation and the OECD provides additional guidance.', 'e86': 'In August 2024, we announced changes to the composition of our segments. These changes align our segments with how we currently manage our business, most notably bringing the commercial components of Microsoft 365 together in the Productivity and Business Processes segment. Beginning in fiscal year 2025, the information that our chief operating decision maker is regularly provided and reviews for purposes of allocating resources and assessing performance reflects these segment changes. Prior period segment information has been recast to conform to the way we internally manage and monitor our business during fiscal year 2025. These changes primarily impacted Note 8 – Goodwill, Note 12 – Unearned Revenue, and Note 18 – Segment Information and Geographic Data.', 'e89': 'Item 8', 'e90': 'On October 13, 2023 , we completed our acquisition of Activision Blizzard, Inc. (“Activision Blizzard”) for a total purchase price of $ 75.4 billion, consisting primarily of cash. Activision Blizzard is a leader in game development and an interactive entertainment content publisher. The acquisition will accelerate the growth in our gaming business across mobile, PC, console, and cloud gaming. The financial results of Activision Blizzard have been included in our consolidated financial statements since the date of the acquisition. Activision Blizzard is reported as part of our More Personal Computing segment.', 'e91': 'Item 8', 'e92': 'As discussed in Note 1 – Accounting Policies, during the first quarter of fiscal year 2025 we made changes to our segments. These segment changes also resulted in changes to our reporting units. We reallocated goodwill across impacted reporting units using a relative fair value approach. In addition, we completed an assessment of any potential goodwill impairment for all reporting units immediately prior to the reallocation and determined that no impairment existed.', 'e93': 'Item 8', 'e94': 'Revenue allocated to remaining performance obligations, which includes unearned revenue and amounts that will be invoiced and recognized as revenue in future periods, was $ 375 billion as of June 30, 2025, of which $ 368 billion is related to the commercial portion of revenue. We expect to recognize approximately 40 % of our total company remaining performance obligation revenue over the next 12 months and the remainder thereafter.', 'e95': 'Item 8', 'e96': 'In its operation of the business, management, including our chief operating decision maker (“CODM”), who is also our Chief Executive Officer , reviews certain financial information, including segmented internal profit and loss statements. The primary profitability measure used by the CODM to review segment operating results is operating income. The CODM uses operating income to allocate resources during our annual planning process and throughout the year, as well as to assess the performance of our segments, primarily by monitoring actual results compared to prior periods and expected results. During the periods presented, we reported our financial performance based on the following segments: Productivity and Business Processes, Intelligent Cloud, and More Personal Computing.'}


@pytest.mark.parametrize("family", ["en", "es", "fr", "zh"])
def test_generic_native_prose_compatible_without_names_or_header_truth(observer, family):
    result = observe(observer, [_PROSE[f"synthetic-{family}-1"], _PROSE[f"synthetic-{family}-2"]],
                     [_PROSE[f"synthetic-{family}-3"]])
    assert result.state == "compatible"
    assert result.output_family == family
    assert result.source_families == (family,)
    assert result.prose_claims == 2
    with pytest.raises(FrozenInstanceError):
        result.state = "different"


@pytest.mark.parametrize("source,output", [("en", "es"), ("en", "fr"), ("en", "zh"),
    ("zh", "en"), ("zh", "es"), ("zh", "fr"), ("es", "en"), ("fr", "en")])
def test_whole_actual_prose_consistently_in_another_language(observer, source, output):
    result = observe(observer, [_PROSE[f"synthetic-{output}-1"], _PROSE[f"synthetic-{output}-2"]],
                     [_PROSE[f"synthetic-{source}-1"]])
    assert (result.state, result.output_family, result.source_families, result.prose_claims) == (
        "different", output, (source,), 2)


def test_actual_saved_twenty_spanish_claims_and_only_their_actual_english_citations(observer):
    # 2026-10-14 saved MiniMax failure; original language header was English.
    # These individual objects are observed, not repaired into an accepted JSON.
    spans = {alias: span(text, index) for index, (alias, text) in enumerate(_SAVED_MM_SPANS.items(), start=1)}
    claims = tuple(claim(text, tuple(spans[alias] for alias in aliases), index)
                   for index, (text, aliases) in enumerate(_SAVED_MM_CLAIMS, start=1))
    result = observer.observe_summary_language(claims, evidence_spans=tuple(spans.values()))
    assert (result.state, result.output_family, result.source_families, result.prose_claims) == (
        "different", "es", ("en",), 20)


def test_chinese_brands_models_foreign_names_and_wuu_share_writing_family(observer):
    result = observe(observer, [_PROSE["zh-brand"], _PROSE["synthetic-zh-6"]], [_PROSE["synthetic-zh-1"]])
    assert (result.state, result.output_family, result.source_families) == ("compatible", "zh", ("zh",))


def test_mixed_cited_english_chinese_still_excludes_third_language(observer):
    result = observe(observer, [_PROSE["synthetic-fr-1"], _PROSE["synthetic-fr-2"]],
                     [_PROSE["synthetic-zh-1"], _PROSE["synthetic-en-1"]])
    assert result.state == "different"
    assert result.output_family == "fr"
    assert result.source_families == ("en", "zh")


def test_unreferenced_foreign_span_does_not_excuse_translation(observer):
    en, es = span(_PROSE["synthetic-en-1"]), span(_PROSE["synthetic-es-1"], 2)
    claims = (claim(_PROSE["synthetic-es-2"], (en,)), claim(_PROSE["synthetic-es-3"], (en,), 2))
    result = observer.observe_summary_language(claims, evidence_spans=(en, es))
    assert (result.state, result.source_families) == ("different", ("en",))


def test_unreferenced_large_foreign_span_is_neither_classified_nor_counted_as_cited_prose(observer):
    en, es = span(_PROSE["synthetic-en-1"]), span("x" * 60_000, 2)
    result = observer.observe_summary_language((claim(_PROSE["synthetic-es-2"], (en,)),), evidence_spans=(en, es))
    assert (result.state, result.source_families) == ("different", ("en",))


def test_english_prose_retains_actual_original_foreign_quotation_and_names(observer):
    quotation = "La nueva línea comenzará a operar el próximo año."
    original = _PROSE["synthetic-en-1"] + " Management stated: ‘" + quotation + "’"
    text = "Management retained the original quotation: ‘" + quotation + "’ " + _PROSE["en-names"]
    result = observe(observer, [text], [original])
    assert (result.state, result.output_family) == ("compatible", "en")


@pytest.mark.parametrize("quote", ['"', '“', '‘', '«', '「'])
def test_entire_verbatim_cited_prose_and_quoted_original_are_compatible(observer, quote):
    right = {'"': '"', '“': '”', '‘': '’', '«': '»', '「': '」'}[quote]
    original = _PROSE["synthetic-es-1"]
    result = observe(observer, [quote + original + right], [original])
    assert result.state == "compatible"
    assert result.prose_claims == 1


def test_actual_cited_verbatim_bilingual_prose_remains_compatible(observer):
    original = _PROSE["synthetic-en-1"] + " " + _PROSE["synthetic-zh-1"]
    result = observe(observer, [original], [original])
    assert result.state == "compatible"
    assert result.output_family is None
    assert result.source_families == ("en", "zh")


@pytest.mark.parametrize("text", ["Item 1", "Item 1A", "2025 93.5% 8.2 9.4", "US$375 billion",
    "Société Lumière", "NanoWave X7", "GaN SiC Al2O3", "Orders rose 12%", "已获重复订单",
    "AlphaBeam BetaScan UltraLight QuantumCore PhotonicSwitch", "RPO 40% 12 months"])
def test_numbers_short_items_models_names_cannot_prove_a_language(observer, text):
    result = observe(observer, [text], [_PROSE["synthetic-en-1"]])
    assert result.state == "uncertain"
    assert result.output_family is None
    assert result.prose_claims == 0


def test_actual_source_with_only_short_item_labels_cannot_be_assumed_english(observer):
    result = observe(observer, [_PROSE["synthetic-es-1"], _PROSE["synthetic-es-2"]], ["Item 1", "Item 7"])
    assert result.state == "uncertain"
    assert result.source_families == ()


def test_single_moderate_claim_is_uncertain_but_long_complete_prose_can_show_difference(observer):
    result = observe(observer, ["Los clientes recibieron pedidos adicionales durante el trimestre."],
                     [_PROSE["synthetic-en-1"]])
    assert result.state == "uncertain"
    longer = observe(observer, [_PROSE["synthetic-es-1"]], [_PROSE["synthetic-en-1"]])
    assert longer.state == "different"


def test_mixed_output_preserves_strong_claim_difference_without_single_aggregate_language(observer):
    result = observe(observer, [_PROSE["synthetic-en-1"], _PROSE["synthetic-es-1"]],
                     [_PROSE["synthetic-en-2"]])
    # Claim-level proof supersedes the old whole-batch abstention: the Spanish
    # claim has substantive English-only citations even beside native English.
    assert result.state == "different"
    assert result.output_family is None


def test_one_claim_with_two_languages_needs_chunk_consensus(observer):
    result = observe(observer, [_PROSE["synthetic-en-1"] + " " + _PROSE["synthetic-es-1"]],
                     [_PROSE["synthetic-en-2"]])
    assert (result.state, result.output_family) == ("uncertain", None)


def test_low_uncalibrated_probability_alone_does_not_reject_correct_long_prose(observer, monkeypatch):
    real = observer._get_identifier()
    monkeypatch.setattr(observer, "_get_identifier", lambda: SimpleNamespace(
        classify=lambda text: (real.classify(text)[0], 0.000001)))
    result = observe(observer, [_PROSE["synthetic-fr-1"], _PROSE["synthetic-fr-2"]],
                     [_PROSE["synthetic-fr-3"]])
    assert result.state == "compatible"


def test_claim_labels_and_aggregate_must_agree(observer, monkeypatch):
    # A single-label aggregate cannot certify either a mixed or contradictory case.
    def classify(text):
        return ("es" if "\n" in text else "en", 1.0)
    monkeypatch.setattr(observer, "_get_identifier", lambda: SimpleNamespace(classify=classify))
    result = observe(observer, [_PROSE["synthetic-en-1"], _PROSE["synthetic-en-2"]],
                     [_PROSE["synthetic-en-3"]])
    assert result.state == "uncertain"
    assert result.output_family is None


@pytest.mark.parametrize("kind", ["claims", "spans", "chars", "claim_chars"])
def test_computation_bounds_abstain_before_identifier_calls(observer, monkeypatch, kind):
    spans = tuple(span(_PROSE["synthetic-en-1"], n) for n in range(1, (98 if kind == "spans" else 3)))
    if kind == "chars":
        spans = (span(_PROSE["synthetic-en-1"] * 260),)
    texts = [_PROSE["synthetic-es-1"]] * (21 if kind == "claims" else 2)
    if kind == "claim_chars":
        texts = [_PROSE["synthetic-es-1"] * 30]
    claims = tuple(claim(text, spans, i) for i, text in enumerate(texts, 1))
    monkeypatch.setattr(observer, "_get_identifier", lambda: pytest.fail("over-bound input must not invoke classifier"))
    assert observer.observe_summary_language(claims, evidence_spans=spans).state == "unavailable"


@pytest.mark.parametrize("fault", [ModuleNotFoundError("missing optional library"), RuntimeError("classifier fault")])
def test_missing_or_failed_library_returns_unavailable_never_default_english(observer, monkeypatch, fault):
    def fail():
        raise fault
    monkeypatch.setattr(observer, "_get_identifier", fail)
    result = observe(observer, [_PROSE["synthetic-es-1"]], [_PROSE["synthetic-en-1"]])
    assert (result.state, result.output_family) == ("unavailable", None)


def test_runtime_classifier_failure_unavailable(observer, monkeypatch):
    def fail(_text):
        raise ValueError("private diagnostic must not escape or become a passed language check")
    monkeypatch.setattr(observer, "_get_identifier", lambda: SimpleNamespace(classify=fail))
    assert observe(observer, [_PROSE["synthetic-es-1"]], [_PROSE["synthetic-en-1"]]).state == "unavailable"


def test_unknown_nonprose_library_label_remains_uncertain(observer, monkeypatch):
    monkeypatch.setattr(observer, "_get_identifier", lambda: SimpleNamespace(classify=lambda _text: ("zxx", 1.0)))
    result = observe(observer, [_PROSE["synthetic-es-1"]], [_PROSE["synthetic-en-1"]])
    assert (result.state, result.output_family) == ("uncertain", None)


def test_same_thread_reuses_identifier_threads_and_pid_do_not_share_it(observer, monkeypatch):
    monkeypatch.setattr(observer, "_IDENTIFIERS", threading.local())
    built = []
    def create():
        built.append(object())
        return built[-1]
    monkeypatch.setattr(observer, "_new_identifier", create)
    monkeypatch.setattr(observer.os, "getpid", lambda: 101)
    first = observer._get_identifier()
    assert observer._get_identifier() is first
    with ThreadPoolExecutor(max_workers=1) as pool:
        second = pool.submit(observer._get_identifier).result()
    assert second is not first
    monkeypatch.setattr(observer.os, "getpid", lambda: 102)
    assert observer._get_identifier() is not first
    assert len(built) == 3


def test_real_identifier_keeps_all_model_languages(observer):
    identifier = observer._get_identifier()
    assert len(set(identifier.nb_classes)) == 140
    assert {"zh", "wuu", "yue", "en", "es", "fr", "zxx"} <= set(identifier.nb_classes)


def test_empty_and_unknown_citation_are_not_language_success(observer):
    assert observer.observe_summary_language((), evidence_spans=()).state == "uncertain"
    source = span(_PROSE["synthetic-en-1"])
    unknown = span(_PROSE["synthetic-es-1"], 2)
    result = observer.observe_summary_language((claim(_PROSE["synthetic-es-2"], (unknown,)),), evidence_spans=(source,))
    assert result.state == "uncertain"


def test_another_claims_foreign_citation_cannot_hide_this_claims_strong_difference(observer):
    en, es = span(_PROSE["synthetic-en-1"]), span(_PROSE["synthetic-es-1"], 2)
    claims = (claim(_PROSE["synthetic-es-2"], (en,)), claim(_PROSE["synthetic-es-3"], (es,), 2))
    result = observer.observe_summary_language(claims, evidence_spans=(en, es))
    # The second Spanish-native claim cannot authorize the first translation.
    assert result.state == "different"
    assert result.source_families == ("en", "es")


def test_short_citations_do_not_hide_a_second_claims_own_strong_difference(observer):
    item, en = span("Item 1"), span(_PROSE["synthetic-en-1"], 2)
    claims = (claim(_PROSE["synthetic-es-2"], (item,)), claim(_PROSE["synthetic-es-3"], (en,), 2))
    result = observer.observe_summary_language(claims, evidence_spans=(item, en))
    # The short-citation claim still lacks proof. The other claim independently
    # establishes a strong difference; no source evidence is borrowed by it.
    assert result.state == "different"


def test_foreign_quotation_not_present_in_own_citation_cannot_be_erased(observer):
    english = span(_PROSE["synthetic-en-1"])
    unreferenced = span(_PROSE["synthetic-es-1"], 2)
    generated = "‘" + _PROSE["synthetic-es-1"] + "’ " + _PROSE["synthetic-en-2"]
    result = observer.observe_summary_language((claim(generated, (english,)),),
                                               evidence_spans=(english, unreferenced))
    assert result.state == "uncertain"
    assert result.output_family is None
    assert result.source_families == ("en",)


@pytest.mark.parametrize("label", ["zh", "wuu", "yue"])
def test_near_chinese_labels_normalize_to_one_writing_family(observer, monkeypatch, label):
    monkeypatch.setattr(observer, "_get_identifier", lambda: SimpleNamespace(classify=lambda _text: (label, 0.5)))
    result = observe(observer, [_PROSE["synthetic-zh-1"], _PROSE["synthetic-zh-2"]],
                     [_PROSE["synthetic-zh-3"]])
    assert (result.state, result.output_family, result.source_families) == ("compatible", "zh", ("zh",))


def test_real_correct_low_probability_chinese_business_prose_is_not_rejected(observer):
    label, score = observer._get_identifier().classify(_PROSE["synthetic-zh-6"])
    assert label in {"zh", "wuu", "yue"}
    assert score < 0.9  # A real counterexample to an invented 0.9 acceptance gate.
    result = observe(observer, [_PROSE["synthetic-zh-6"]], [_PROSE["synthetic-zh-1"]])
    assert (result.state, result.output_family) == ("compatible", "zh")


def test_repeated_citations_count_unique_span_characters_once(observer):
    original = span(_PROSE["synthetic-en-1"] * 16)
    claims = tuple(claim(_PROSE["synthetic-en-1"], (original,), index) for index in range(1, 21))
    result = observer.observe_summary_language(claims, evidence_spans=(original,))
    assert (result.state, result.prose_claims) == ("compatible", 20)


# Static software/model identity: no installed library or classifier is changed.
@pytest.fixture
def language_identity_files(observer, tmp_path, monkeypatch):
    code = tmp_path / "langid.py"
    weights = tmp_path / "model.bin"
    sentinel = tmp_path / "keep.bin"
    code.write_bytes(b"def classify(text):\n    return 'en', 1.0\n")
    weights.write_bytes(b"\x00model weights\xff\r\n")
    sentinel.write_bytes(b"existing fixture sentinel")
    module = SimpleNamespace(__file__=str(code), MODEL_FILE=str(weights))
    distributions = {"py3langid": "0.4.0", "numpy": "2.0.0"}
    monkeypatch.setattr(observer, "import_module", lambda name: module, raising=False)
    monkeypatch.setattr(observer, "distribution_version", lambda name: distributions[name], raising=False)
    yield module, code, weights, distributions
    assert sentinel.read_bytes() == b"existing fixture sentinel"


def test_observer_identity_binds_actual_code_raw_weights_and_distributions(observer, language_identity_files):
    _module, code, weights, _versions = language_identity_files
    actual = observer.language_observer_identity()
    assert actual["schema_version"] == "narrative-language-observer/1"
    assert actual["py3langid"]["status"] == "available"
    assert actual["py3langid"]["version"] == "0.4.0"
    assert actual["py3langid"]["module"] == {"status": "available", "sha256": hashlib.sha256(code.read_bytes()).hexdigest(), "bytes": len(code.read_bytes())}
    assert actual["py3langid"]["model"] == {"status": "available", "sha256": hashlib.sha256(weights.read_bytes()).hexdigest(), "bytes": len(weights.read_bytes())}
    assert actual["numpy"] == {"distribution": "numpy", "version": "2.0.0", "status": "available"}
    assert str(code.parent) not in str(actual)


def test_weights_change_missing_and_restoration_invalidate_without_version_bump(observer, language_identity_files):
    _module, _code, weights, _versions = language_identity_files
    original = weights.read_bytes()
    baseline = observer.language_observer_identity()
    weights.write_bytes(original + b" changed")
    assert observer.language_observer_identity() != baseline
    weights.unlink()
    missing = observer.language_observer_identity()
    assert missing["py3langid"]["status"] == "unavailable"
    assert missing["py3langid"]["model"] == {"status": "unavailable", "sha256": None, "bytes": None}
    weights.write_bytes(original)
    assert observer.language_observer_identity() == baseline


def test_observer_identity_other_paths_and_code_crlf_are_content_equivalent(observer, language_identity_files, tmp_path):
    module, code, weights, _versions = language_identity_files
    baseline = observer.language_observer_identity()
    relocated = tmp_path / "relocated"
    relocated.mkdir()
    new_code, new_weights = relocated / "langid.py", relocated / "model.bin"
    new_code.write_bytes(code.read_bytes().replace(b"\n", b"\r\n"))
    new_weights.write_bytes(weights.read_bytes())
    module.__file__, module.MODEL_FILE = str(new_code), str(new_weights)
    assert observer.language_observer_identity() == baseline
    new_code.write_bytes(new_code.read_bytes() + b"# different classifier code\n")
    assert observer.language_observer_identity() != baseline


@pytest.mark.parametrize("component", ["py3langid", "numpy"])
def test_distribution_missing_and_version_changes_are_observable(observer, language_identity_files, monkeypatch, component):
    _module, _code, _weights, versions = language_identity_files
    baseline = observer.language_observer_identity()
    versions[component] = "different-version"
    assert observer.language_observer_identity() != baseline
    def missing(name):
        if name == component:
            raise importlib.metadata.PackageNotFoundError(name)
        return versions[name]
    monkeypatch.setattr(observer, "distribution_version", missing)
    absent = observer.language_observer_identity()
    assert absent[component]["status"] == "unavailable" and absent[component]["version"] is None


def test_missing_identifier_module_and_model_field_are_explicit(observer, language_identity_files, monkeypatch):
    module, _code, _weights, _versions = language_identity_files
    def unavailable(_name):
        raise ModuleNotFoundError("no classifier module")
    monkeypatch.setattr(observer, "import_module", unavailable)
    missing = observer.language_observer_identity()
    assert missing["py3langid"]["module"]["status"] == "unavailable"
    monkeypatch.setattr(observer, "import_module", lambda _name: module)
    del module.MODEL_FILE
    assert observer.language_observer_identity()["py3langid"]["model"]["status"] == "unavailable"


def test_static_digest_memo_is_bounded_detached_and_does_not_rehash_same_weights(observer, language_identity_files, monkeypatch, tmp_path):
    module, _code, weights, _versions = language_identity_files
    calls = []
    read = Path.open
    def tracked(path, *args, **kwargs):
        if path == weights:
            calls.append(path)
        return read(path, *args, **kwargs)
    monkeypatch.setattr(Path, "open", tracked)
    baseline = observer.language_observer_identity()
    for _ in range(100):
        assert observer.language_observer_identity() == baseline
    assert len(calls) == 1
    baseline["py3langid"]["model"]["sha256"] = "wrong"
    assert observer.language_observer_identity()["py3langid"]["model"]["sha256"] != "wrong"
    for index in range(30):
        path = tmp_path / f"weight-{index}.bin"
        path.write_bytes(bytes([index]))
        module.MODEL_FILE = str(path)
        observer.language_observer_identity()
    assert len(observer._LANGUAGE_RESOURCE_DIGESTS) <= 16


def test_installed_relative_model_identity_matches_library_resource(observer, monkeypatch):
    from py3langid import langid

    # Use the installed library's public resource ports, never a private filename
    # assumption or a copied/generic test model. Do not construct a classifier.
    model_file = Path(langid.MODEL_FILE)
    if not model_file.is_absolute():
        model_file = Path(langid.MODEL_DIR) / model_file
    assert model_file.is_file()
    monkeypatch.setattr(observer, "_new_identifier", lambda: pytest.fail("identity must not load a classifier"))
    actual = observer.language_observer_identity()
    code = Path(langid.__file__).read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    weights = model_file.read_bytes()
    assert actual["py3langid"]["status"] == "available"
    assert actual["py3langid"]["module"] == {
        "status": "available", "sha256": hashlib.sha256(code).hexdigest(), "bytes": len(code)}
    assert actual["py3langid"]["model"] == {
        "status": "available", "sha256": hashlib.sha256(weights).hexdigest(), "bytes": len(weights)}


def test_relative_model_uses_library_base_instead_of_cwd(observer, language_identity_files, tmp_path, monkeypatch):
    module, _code, weights, _versions = language_identity_files
    baseline = observer.language_observer_identity()
    library = tmp_path / "library-install"
    resources = library / "resources"
    resources.mkdir(parents=True)
    (resources / "weights.bin").write_bytes(weights.read_bytes())
    cwd = tmp_path / "working-directory"
    (cwd / "resources").mkdir(parents=True)
    (cwd / "resources/weights.bin").write_bytes(b"wrong cwd resource must not be used")
    module.MODEL_FILE, module.MODEL_DIR = "resources/weights.bin", library
    monkeypatch.chdir(cwd)
    assert observer.language_observer_identity() == baseline


def test_relative_model_relocation_change_missing_and_restoration_are_observable(observer, language_identity_files, tmp_path):
    module, _code, weights, _versions = language_identity_files
    original = weights.read_bytes()
    baseline = observer.language_observer_identity()
    module.MODEL_FILE = "assets/arbitrary-weight.bin"
    for name in ("install-one", "install-two"):
        library = tmp_path / name
        model_file = library / module.MODEL_FILE
        model_file.parent.mkdir(parents=True)
        model_file.write_bytes(original)
        module.MODEL_DIR = library
        assert observer.language_observer_identity() == baseline
    model_file.write_bytes(original + b" changed")
    assert observer.language_observer_identity() != baseline
    model_file.unlink()
    missing = observer.language_observer_identity()
    assert missing["py3langid"]["status"] == "unavailable"
    assert missing["py3langid"]["model"] == {"status": "unavailable", "sha256": None, "bytes": None}
    model_file.write_bytes(original)
    assert observer.language_observer_identity() == baseline


@pytest.mark.parametrize("base", [None, False])
def test_relative_model_invalid_base_cannot_borrow_cwd_weights(observer, language_identity_files, monkeypatch, base):
    module, code, weights, _versions = language_identity_files
    module.MODEL_FILE, module.MODEL_DIR = weights.name, base
    monkeypatch.chdir(code.parent)
    actual = observer.language_observer_identity()
    assert actual["py3langid"]["status"] == "unavailable"
    assert actual["py3langid"]["model"] == {"status": "unavailable", "sha256": None, "bytes": None}


def test_relative_model_absolute_path_ignores_invalid_library_base(observer, language_identity_files):
    module, _code, _weights, _versions = language_identity_files
    baseline = observer.language_observer_identity()
    module.MODEL_DIR = None
    assert observer.language_observer_identity() == baseline
