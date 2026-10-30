"""Bound operating-predicate patterns for the DU4-STATE detector.

Every pattern binds a predicate phrase (``pred``) to its qualifier markers
(``qual``), object (``obj``) or counterpart (``partner``) within a bounded
window. A predicate alone — a noun compound such as 生产瓶颈 or a bare list
like 产品认证与商业化 — never becomes an assertion. Matching runs on the
converted reading view; refs map back to original offsets elsewhere.
"""

from __future__ import annotations

import re

# Noun-compound heads: 生产/认证 immediately followed by these is a noun
# modifier ("不是生产瓶颈"), never an operating predicate.
COMPOUND_HEAD = (
    r"瓶颈|问题|难题|线|车间|基地|模式|工艺|流程|成本|效率|设备|能力|规模|"
    r"厂商|企业|环节|要素|大国|强国|机构|体系|标准|费用|周期|进度|地区|地域|"
    r"mechanism|bottleneck|issue|problem|line|site|facility|process|cost|"
    r"efficiency|capability|scale|plant|sector|industry|body|scheme"
)
# Non-product operating themes use the same subject/object binder, without
# pretending that a channel or distribution network is a product declaration.
OPERATING_THEME_HEAD = re.compile(r"(?:渠道|通路|经销网络|销售网络|交付地区|交付地域|"
    r"(?:distribution|sales|delivery)\s+(?:channels?|networks?|regions?))\s*$",re.I)
_NOT_COMPOUND = rf"(?!\s*(?:{COMPOUND_HEAD}))"

_CJK_OBJ = r"[\w㐀-鿿（）()\- ]{1,24}"
_CJK_OBJ_SHORT = r"[㐀-鿿\w\-]{1,12}"
_EN_OBJ = r"\s+(?:[A-Za-z][\w\-'&]*\s*){1,4}"

_ABSENCE = (
    r"现无|现無|现不|现在不|目前(?:並|并)?(?:未|无|不)|不存在|并没有|并不|并未|不再|"
    r"尚未|还未|暂未|仍未|从来没有|从未|未曾|不曾|没有再|没有|未|无|不"
)
# Abstract risk/issue nouns are never operating objects: "不存在经营风险"
# is risk language, not a business-scope assertion.
ABSTRACT_OBJECT = re.compile(
    r"风险|風險|风险点|風險點|风险问题|问题|問題|难题|難題|挑战|挑戰|"
    r"不确定性|不確定性|隐患|隱患|困难|困難|障碍|障礙|经营风险|經營風險|"
    r"risk|risks|issue|issues|challenge|challenges|uncertainty|uncertainties|"
    r"concern|concerns|problem|problems",
    re.IGNORECASE,
)
_SUSPEND = r"暂停|中止|暂缓|暂时停止"
_STOP = r"停产|停產|停止|终止|終止|关停|关闭"

# One predicate-local modifier grammar, shared across event families. This is
# a contiguous suffix, never a document-wide keyword/co-occurrence classifier.
PLANNED_QUAL = re.compile(r"计划|拟|规划|打算|即将|将要|\b(?:plans?|planned|intend\w*|aims?|will)\b", re.IGNORECASE)
ASPIRATIONAL_QUAL = re.compile(r"希望|期望|期盼|期待|愿|\b(?:hopes?|wish\w*)\b", re.IGNORECASE)
MODIFIER_TOKENS = re.compile(
    rf"并非|并不是|不是|{_ABSENCE}|计划|拟|规划|打算|即将|将要|希望|期望|愿|已经|已|正在"
    r"|\b(?:has|have|had|is|are|was|were|do|does|did|will|would|could|may|might|not|never|yet|"
    r"currently|already|plans?|planned|intends?|aims?|hopes?|to)\b", re.IGNORECASE)
MODIFIER_BRIDGE = re.compile(
    r"\s*(?:(?:正式|最终|最终正式|实际|直接|持续|继续|进一步|目前|"
    r"formally|officially|actually|directly|currently|still)\s*|"
    r"(?:与|向|对|和|with\b|for\b)\s*[\w㐀-鿿（）()\- ]{1,24}?\s*)*",re.IGNORECASE)
MODIFIER_SCOPE_BREAK = re.compile(r"但是|然而|但|而非|\b(?:but|however|whereas)\b",re.IGNORECASE)
NEGATION_TOKENS = re.compile(rf"并非|并不是|不是|{_ABSENCE}|\b(?:not|never)\b",re.IGNORECASE)
CONDITION_ONLY = re.compile(r"如果|若|一旦|\bif\b",re.IGNORECASE)
HYPOTHETICAL_QUAL = re.compile(r'\b(?:would|could|may|might)\b',re.IGNORECASE)
ATTRIBUTIVE_PARTY = re.compile(
    r'^的(?P<actor>[\w㐀-鿿\-]{0,10}?(?:供应商|供應商|客户|客戶|子公司|母公司|股东|股東))')

# ---------------------------------------------------------------- events
# Each entry: (construction name, activity, compiled regex).
# Group names used: pred (required), qual, obj, obj_lead, partner, restriction.

PRODUCTION_NEGATION = re.compile(
    rf"(?P<qual>{_ABSENCE})(?P<pred>生产|制造|量產|量产|投产|投產|加工)"
    rf"{_NOT_COMPOUND}(?P<obj>{_CJK_OBJ})?"
)
PRODUCTION_SUSPEND = re.compile(
    rf"(?P<qual>{_SUSPEND})(?:了|其)?(?P<obj>[\w㐀-鿿\-]{{0,10}}?)?"
    rf"(?P<pred>生产|制造|供货|发货|交付|运营){_NOT_COMPOUND}"
)
PRODUCTION_STOP = re.compile(
    rf"(?P<obj>[\w㐀-鿿\-]{{1,10}}?)(?P<pred>{_STOP})"
    rf"(?!生产|制造|量产|投产|加工){_NOT_COMPOUND}"
)
PRODUCTION_STOP_ACTION = re.compile(
    rf'(?P<qual>{_STOP})(?P<pred>生产|制造|量产|投产|加工){_NOT_COMPOUND}(?P<obj>{_CJK_OBJ})?')
PRODUCTION_ASPECT = re.compile(
    rf"(?P<qual>非批量|非量产|已|已经|完成|实现|开始|正式|重新|正在|即将|"
    rf"逐步|稳定)(?:批量|小批量|分批|陆续)?"
    rf"(?P<pred>生产|制造|量產|量产|投产|投產){_NOT_COMPOUND}(?P<obj>{_CJK_OBJ})?"
)
PRODUCTION_EN = re.compile(
    r"(?P<qual>(?:do|does|did)\s+not(?:\s+currently)?|no\s+longer|not\s+currently|"
    r"never|not|is\s+not|are\s+not)?\s*"
    r"(?P<pred>manufactur(?:e|es|ed|ing)|produc(?:e|es|ed|ing)|mak(?:e|es|ing))"
    r"(?P<obj>" + _EN_OBJ + r")?",
    re.IGNORECASE,
)
PRODUCTION_EN_SUSPEND = re.compile(
    r"(?P<qual>suspend(?:s|ed|ing)?|halt(?:s|ed)?|ceas(?:e|es|ed|ing)|"
    r"stopp?(?:s|ed|ing)?|interrupt(?:s|ed)?)\s+"
    r"(?P<pred>production|manufacturing|supply|supplies|shipping)"
    r"(?:\s+of\s+(?P<obj>[\w\-'&]+(?:\s+[\w\-'&]+){0,3}))?",
    re.IGNORECASE,
)

COMMERCIALIZATION = re.compile(
    rf"(?P<qual>{_ABSENCE}|已|已经|完成|实现|计划|拟|推迟|启动|加快|推进)?"
    rf"(?P<pred>商业化|商業化|上市销售|对外销售|公開銷售|公开销售|面市)"
    rf"{_NOT_COMPOUND}(?P<obj>{_CJK_OBJ})?"
)
COMMERCIALIZATION_EN = re.compile(
    r"(?P<qual>is\s+not|are\s+not|not\s+yet|not|no\s+longer|never|remains?|"
    r"remain)?\s*"
    r"(?P<pred>commerciali[sz](?:e|es|ed|ing|ation)|commercial\s+sale|"
    r"commercially\s+available|available\s+for\s+commercial\s+sale)"
    r"(?P<obj>" + _EN_OBJ + r")?",
    re.IGNORECASE,
)

QUALIFICATION_PENDING = re.compile(
    rf"(?P<qual>{_ABSENCE}|仍需|尚需|还需|有待|尚待)(?:取得|获得|获取|拿到|获|obtained?)?"
    rf"(?:客户|customer\s+)?(?:对其|对其)?(?:完成|通过|取得|获得)?"
    # This slot may name a certification class or an explicit product entity;
    # the shared noun-phrase role owner resolves it before subject inheritance.
    rf"(?P<qualification_argument>{_CJK_OBJ_SHORT}?)?的?(?P<pred>认证|認證|qualification|validation)"
    rf"{_NOT_COMPOUND}"
)
QUALIFICATION_RESULT = re.compile(
    r"(?P<obj_lead>客户|第三方|供应商|权威机构)?"
    r"(?P<pred>验证|驗證|认证|認證|资质审核)"
    r"(?P<qual>未通过|未獲|未获通过|未获认证|失败|未成功|附条件通过|附条件|"
    r"已通过|通过|通過|获批|获证)"
)
QUALIFICATION_VERB = re.compile(
    rf"(?P<qual>完成|通过|通過|取得|获得|獲取|获批)?"
    rf"(?P<obj_lead>客户|第三方|供应商)?"
    rf"(?P<pred>验证|驗證|认证|認證){_NOT_COMPOUND}"
)
QUALIFICATION_EN = re.compile(
    r"(?P<qual>has\s+not|have\s+not|had\s+not|is\s+not|are\s+not|not\s+yet|"
    r"not|never)?\s*"
    r"(?:obtain(?:s|ed|ing)?|receiv(?:e|es|ed|ing)|gain(?:s|ed)?|secur(?:e|es|ed))?\s*"
    r"(?:customer\s+)?(?P<pred>qualification|certification|approval|validation)"
    r"(?:\s+(?P<state>is\s+obtained|are\s+obtained|has\s+been\s+obtained|"
    r"was\s+obtained|is\s+secured|is\s+granted))?"
    r"(?P<obj>" + _EN_OBJ + r")?",
    re.IGNORECASE,
)
QUALIFICATION_PENDING_EN = re.compile(
    r"(?P<pred>qualification|certification|approval|validation)\s+"
    r"(?P<qual>remains?\s+pending|remain\s+pending|is\s+pending|are\s+pending|"
    r"has\s+not\s+been\s+obtained|is\s+still\s+outstanding)",
    re.IGNORECASE,
)
APPROVAL_RESTRICTED = re.compile(
    r"(?P<pred>approved|approvals?)\s+"
    r"(?P<restriction>only\s+for\s+pilot\s+use(?:\s+only)?|for\s+pilot\s+use\s+only|"
    r"solely\s+for\s+pilot(?:\s+use)?|only\s+for\s+trial(?:\s+use)?)",
    re.IGNORECASE,
)
UNSUCCESSFUL_VALIDATION = re.compile(
    r"(?P<qual>unsuccessful|failed|not\s+successful|unfavorable)\s+"
    r"(?P<pred>validation|qualification|certification)",
    re.IGNORECASE,
)

SHIPMENT = re.compile(
    rf"(?P<qual>{_ABSENCE}|已|已经|完成|开始|即将|稳定|批量)?"
    rf"(?:向(?P<partner>{_CJK_OBJ_SHORT}))?"
    rf"(?:批量|小批量|分批|陆续)?"
    rf"(?P<pred>发货|出货|交付|供货|交貨){_NOT_COMPOUND}(?P<obj>{_CJK_OBJ})?"
)
SHIPMENT_EN = re.compile(
    r"(?P<qual>shipped|shipments?\s+(?:began|started|have\s+started)|"
    r"began\s+shipping|started\s+(?:to\s+)?ship|deliver(?:s|ed|ing)?|"
    r"suspend(?:s|ed)?\s+shipments?)"
    r"(?:\s+to\s+(?P<partner>[\w\-'&]+(?:\s+[\w\-'&]+){0,2}))?"
    r"(?P<obj>" + _EN_OBJ + r")?",
    re.IGNORECASE,
)

SCOPE_CN = re.compile(
    rf"(?P<qual>{_ABSENCE}|已|已经)?"
    rf"(?P<pred>涉及|參與|参与|涉足|从事|從事|經營|经营|开展业务)"
    rf"{_NOT_COMPOUND}(?P<obj>{_CJK_OBJ})?"
)
# A predicate-shaped stem inside a derived person/attribute noun is not a
# finite scope predicate. Outline markers likewise cannot act as its subject.
SCOPE_NOMINAL_SUFFIX = re.compile(r"者|人员|人員|机构|機構|性|性的")
OUTLINE_PREFIX = re.compile(r"^\s*(?:[(（]\s*(?:[ivxlcdmIVXLCDM]+|\d+|[一二三四五六七八九十]+)\s*[)）]|[ivxlcdmIVXLCDM]+[.、])\s*")
SCOPE_EN = re.compile(
    r"(?P<qual>is\s+not|are\s+not|not|no\s+longer|never)?\s*"
    r"(?P<pred>involved\s+in|engaged\s+in|participating\s+in|active\s+in|"
    r"present\s+in)"
    r"(?P<obj>" + _EN_OBJ + r")?",
    re.IGNORECASE,
)

RELATION_CONTACT = re.compile(
    rf"(?:(?P<qual>已经|已|曾經|曾经|近期|近日)?"
    rf"(?P<pred>建立了?联系|建立沟通|建立了?沟通|進行了?技术接洽|进行了?技术接洽|"
    rf"技术接洽|技术交流|接洽|洽谈|会谈|沟通交流))|"
    rf"(?P<qual2>已|已经)?(?:与(?P<partner>{_CJK_OBJ_SHORT}?))"
    rf"(?=就|在|关于|对|等|，|。|、|进行|开展|签署|建立|已|将|洽谈|接洽)",
)
RELATION_CONTACT_EN = re.compile(
    r"(?:(?P<qual>has\s+|have\s+)?(?P<pred>held\s+(?:technical\s+)?(?:discussions|talks)|"
    r"established\s+(?:contact|communication)|contacted|in\s+contact\s+with|"
    r"entered\s+(?:into\s+)?(?:discussions|talks|negotiations)))"
    r"(?:\s+(?:with\s+)?(?P<partner>[\w\-'&]+(?:\s+[\w\-'&]+){0,2}?))?"
    r"(?=\s+(?:about|on|for|and|to|regarding|in|over|from)\b|[.,;]|$)",
    re.IGNORECASE,
)
RELATION_SIGN = re.compile(
    r"(?P<qual>已|已经)?(?P<pred>签署|签订|签约)"
    r"(?P<obj>采购合同|供货合同|供货协议|合作协议|合同|协议|purchase\s+contract|"
    r"supply\s+agreement)"
)
RELATION_SIGN_EN = re.compile(
    r"(?P<qual>has\s+|have\s+)?(?P<pred>sign(?:s|ed)?|conclud(?:e|es|ed)|execut(?:e|es|ed))\b"
    r"(?P<obj>" + _EN_OBJ + r")?",
    re.IGNORECASE,
)
RELATION_INTENDED = re.compile(
    rf"(?P<qual>希望|期望|期盼|期待|願|愿)"
    rf"(?:与(?P<partner>{_CJK_OBJ_SHORT}?))?(?:能|可以)?"
    rf"(?P<pred>建立|开展|推动|推进|形成|促成|保持)"
    rf"(?P<obj>[㐀-鿿]{{0,10}}?(?:业务协同与合作|业务合作|合作关系|沟通与合作|"
    rf"合作|协同))?"
)
RELATION_INTENDED_EN = re.compile(
    r"(?P<qual>hope|hopes|wish|wishes|look\s+forward\s+to|expect|expects)"
    r"(?:\s+to)?\s*(?:\s*(?:continued|further|future|closer)\s+)?"
    r"(?P<pred>cooperat\w*|collaborat\w*|communicat\w*|work\s+together|"
    r"partnership|establish\s+contact)",
    re.IGNORECASE,
)
RELATION_PLAN = re.compile(
    rf"(?P<qual>计划|拟|規劃|规划|打算)"
    rf"(?:与(?P<partner>{_CJK_OBJ_SHORT}?))?(?:能|可以)?"
    rf"(?P<pred>开展|建立|推动|推进|形成|拓展|进入)"
    rf"(?P<obj>[㐀-鿿]{{0,10}}?(?:业务合作|业务协同与合作|合作关系|合作|协同))?"
)
RELATION_PLAN_EN = re.compile(
    r"(?P<qual>plan|plans|planned|intend|intends|aim|aims|expect|expects)"
    r"(?:\s+to)?\s*"
    r"(?P<pred>cooperat\w*|collaborat\w*|establish|build|develop|expand|enter)"
    r"(?P<obj>" + _EN_OBJ + r")?",
    re.IGNORECASE,
)
COMMERCIAL_PLAN_EN = re.compile(
    r"(?P<qual>plan|plans|planned|intend|intends|aim|aims|expect|expects)"
    r"(?:\s+to)?\s*"
    r"(?P<pred>commerciali[sz]\w*)"
    r"(?P<obj>" + _EN_OBJ + r")?",
    re.IGNORECASE,
)

UNCERTAIN_SCOPE = re.compile(
    rf"(?P<qual>无法确定|暂无法确定|无法判断|尚不明确|不确定|无法甄别|难以确定)"
    rf"(?:是否|是否为|是否已经)?"
    rf"(?P<pred>涉及|參與|参与|涉足|生产|制造|商业化|经营)"
    rf"(?P<obj>{_CJK_OBJ})?"
)
UNCERTAIN_EN = re.compile(
    r"(?P<qual>cannot\s+(?:be\s+)?(?:determined|confirmed|verified)|it\s+is\s+unclear|"
    r"unclear\s+whether|not\s+certain\s+whether|unable\s+to\s+determine)"
    r"(?:\s+whether)?(?:\s+we(?:\s+are)?)?"
    r"(?P<pred>involved\s+in|producing|manufacturing|commerciali[sz]\w*)"
    r"(?P<obj>" + _EN_OBJ + r")?",
    re.IGNORECASE,
)
DOUBLE_NEGATION = re.compile(
    r"(?P<qual>并非没有|不是没有|未尝没有|并非不|not\s+that\s+(?:we\s+)?(?:have\s+)?no)"
    r"(?P<pred>生产|制造|商业化|涉及|生產|經營)"
)



# ---------------------------------------------------------------- clause guards

INTERROGATIVE_PREFIX = re.compile(
    r"^\s*(?:请问|是否|有没有|能(?:否)?|可否|为什么|为何|怎么|怎样|如何|哪|"
    r"what|who|when|where|why|how|whether)\b",
    re.IGNORECASE,
)
INTERROGATIVE_MARKER = re.compile(
    r"问[：:]|Q[：:]|哪些|哪个|多少|何时|多久|何处|吗[？?]?|呢[？?]?|\?$|？$",
    re.IGNORECASE,
)
INTERROGATIVE_OPERATOR = re.compile(r"是否|能否|\bwhether\b", re.IGNORECASE)
NEGATED_PROPOSITION_OPERATOR = re.compile(
    r"否认|否認|否定|辟谣|闢謠|\bden(?:y|ies|ied|ying)\b", re.IGNORECASE)
DEFINITION = re.compile(
    r"是指|定义为|定义為|的定义|的定義|术语表|術語表|词汇表|詞彙表|术语|術語|"
    r"is defined as|defined as|refers to as|\bmeans\b|glossary|definition\s*[:：]|"
    r"定义如下",
    re.IGNORECASE,
)
ADMIN_RECEIPT = re.compile(
    r"(?:未|没有|沒)收到[^。！？!?]{0,15}(?:提问|问题|通知|问询|咨询|反馈|函)|"
    r"(?:questions?|notices?|inquiries?|comments?|feedback)[^.!?]{0,25}"
    r"(?:received|not received)|(?:not|no|never)\s+(?:any\s+)?"
    r"(?:questions?|notices?|inquiries?)\s+(?:were\s+)?received",
    re.IGNORECASE,
)
GENERIC_WISH = re.compile(
    r"(?:期待|希望|期盼|期望|願)[^。！？!?]{0,25}"
    r"(?:一切顺利|一切.{0,4}顺利|越来越好|圆满|成功|顺利|蓬勃发展|再创辉煌|"
    r"蒸蒸日上|保持沟通|保持联系|加强沟通|共同(?:发展|进步)|多沟通)|"
    r"(?:hope|expect|look\s+forward\s+to|wish)[^.!?]{0,60}"
    r"(?:go\s+well|all\s+the\s+best|continued\s+(?:communication|cooperation|"
    r"success|growth)|greater\s+success)",
    re.IGNORECASE,
)
COURTESY = re.compile(
    r"感谢[^。！？!?]{0,20}(?:关注|支持|厚爱|阅读)|"
    r"thank\s+you\s+for\s+your\s+(?:interest|attention|support|time)",
    re.IGNORECASE,
)
VISION = re.compile(
    r"致力于成为|致力於成為|致力于打造|愿景是|願景是|目标是成为|目標是成為|"
    r"strive\s+to\s+become|aim\s+to\s+be|committed\s+to\s+becoming|"
    r"vision\s+to\s+(?:be|become)",
    re.IGNORECASE,
)
FINANCIAL_COMPOSITION = re.compile(
    r"(?:分部|板块|segment)[^。.!?]{0,30}(?:包括|由|构成|comprises?|consists?|"
    r"comprised|includes?)[^。.!?]{0,40}(?:营业收入|营收|收入|利润|revenue|profit|"
    r"income)|(?:营业收入|营收|收入|利润|revenue|profit)[^。.!?]{0,20}"
    r"(?:组成|构成|comprise|consist)",
    re.IGNORECASE,
)
RESTRICTION_CONTINUATION = re.compile(
    r"^\s*(?:仅|只有|只是|僅|仅供|仅用于|用于|only|solely)\s*.{0,10}?"
    r"(?:试用|試用|试验|試驗|pilot|trial)",
    re.IGNORECASE,
)
TIME_WORD = re.compile(
    r"第[一二三四1-4]季度|今年|明年|去年|后年|未来|目前|下旬|上旬|中旬|"
    r"^\d+$|[年月日]$|next\s+(?:year|quarter|month)|this\s+(?:year|quarter)",
    re.IGNORECASE,
)
FUTURE_TIME = re.compile(
    r"第[一二三四1-4]季度|明年|今年下半年|未来|下一年|即将|拟于|将会|下(?:个|一)?月|下(?:个|一)?季度|"
    r"next\s+(?:year|quarter|month)|in\s+the\s+(?:coming|next)",
    re.IGNORECASE,
)
PAST_TIME = re.compile(
    r"去年|上年|上(?:个|一)?月|上(?:个|一)?季度|此前|"
    r"\b(?:last|prior|previous)\s+(?:year|quarter|month|period)\b", re.I)
CURRENT_TIME = re.compile(
    r"报告期内|报告期|本期|本年度|目前|今年|"
    r"\bthis\s+(?:year|quarter|month|period)\b|"
    r"\b(?:during|in|for)\s+the\s+(?:(?:reporting|current)\s+)?period\b", re.I)
ACTION_TEMPORAL_FRAME = re.compile(
    rf"(?:(?:在|于)\s*)?(?:{PAST_TIME.pattern}|{CURRENT_TIME.pattern}|{FUTURE_TIME.pattern})", re.I)
CONDITIONAL = re.compile(
    r"如果|若|一旦|前提|条件下|附条件|subject\s+to|upon\s+(?:obtaining|receiving)|"
    r"if\s+.{0,40}(?:is\s+obtained|are\s+met|is\s+approved|is\s+granted|passes)",
    re.IGNORECASE,
)

# ---------------------------------------------------------------- actors

ACTOR_CUT = re.compile(
    r"(?:因|由于|因为|根据|基于|通过|以|为|于|after|because|due\s+to|following|"
    r"given|based\s+on|per)\s*",
    re.IGNORECASE,
)
EN_AUX_BOUNDARY = re.compile(
    r"\b(?:remains?|remained|includes?|included|comprises?|comprised|consists?|"
    r"provides?|offered?|offers?|covers?|features?|develops?|produces?|"
    r"manufactures?|sells?|ships?|uses?|focuses?|targets?|operates?|manages?|"
    r"was|were|is|are|has|have|had|will|would|can|could|may|might|must|shall|"
    r"should|do|does|did|and|but|or|yet|so|then|also|still|just|not|never)\b",
    re.IGNORECASE,
)
SUBJECT_TAIL = re.compile(
    r"(?:已经|已經|已|正在|目前|当前|當前|现在|現在|尚未|还是|還是|将|把|被|曾|"
    r"从来|也|还|而|并|並且|并且|且|同时|以及|"
    r"(?<![A-Za-z])(?:and|also|then|while|but|however|now|currently|just|still|already|ever|"
    r"is|are|was|were|has|have|had|be|been|being|will|would|can|could|may|"
    r"might|must|shall|should|do|does|did|to|the|a|an|its|their|our|this|that|"
    r"in|on|at|of|for|with|about|from))\s*$",
    re.IGNORECASE,
)
CN_TOPIC_BOUNDARY = re.compile(
    r"正在|仍在|仍旧|处于|處於|进行|進行|开始|開始|持续|持續|不断|不斷|已经|已經|"
    r"目前|现在|現在|尚未|还是|還是|保持|完成|实现|實現|成为|成為|"
    r"不是|并非|并不|不再"
)
CONJUNCT_SPLIT = re.compile(r"与|與|和|及|、|&|\band\b", re.IGNORECASE)
PRODUCT_SUFFIX = re.compile(
    r"(?:产品|產品|设备|設備|材料|添加剂|產線|产线|模组|模块|器件|试剂|药品|"
    r"service|product|platform|system|prototype|device|additive|chemical|"
    r"solution|tool|tools|equipment|line|membrane|resin|filter|filters|"
    r"material|module|sensor|panel|film|coating)$",
    re.IGNORECASE,
)
RELATED_PARTY = re.compile(
    r"控股股东|控股股東|实际控制人|實際控制人|母公司|子公司|关联方|關聯方|"
    r"集团公司|集團公司|股东|股東|parent|subsidiary|affiliate|affiliates|"
    r"controlling\s+shareholder|shareholder|our\s+parent|our\s+subsidiary",
    re.IGNORECASE,
)
THIRD_PARTY = re.compile(
    r"供应商|供应商|客戶|客户|第三方|对手方|對手方|合作方|承包商|"
    r"supplier|suppliers|customer|customers|third[- ]party|counterparty|"
    r"counterpart|contractor|vendor|distributor",
    re.IGNORECASE,
)
ISSUER_WORD = re.compile(
    r"公司|本公司|本集团|本集團|本企业|本企業|我们|我們|"
    r"(?:the|our|this)\s+company|our\s+company|\bwe\b|\bour\b",
    re.IGNORECASE,
)
CUE_RELATED = re.compile(
    r"(控股股东|控股股東|实际控制人|實際控制人|母公司|子公司|关联方|關聯方|"
    r"集团公司|集團公司|股东|股東|parent|subsidiary|affiliate|"
    r"controlling\s+shareholder|shareholder)"
    r"(?P<name>[㐀-鿿\w\-]{2,12}?)(?=信息|表示|介绍|介紹|称|稱|指出|获悉|"
    r"消息|方面|，|。|、|；|;|\s|$|表示)",
    re.IGNORECASE,
)
CUE_THIRD = re.compile(
    r"(供应商|供應商|客户|客戶|第三方|对手方|對手方|合作方|承包商|"
    r"supplier|customer|third[- ]party|counterparty|contractor|vendor)"
    r"(?P<name>[㐀-鿿\w\-]{2,12}?)(?=信息|表示|介绍|介紹|称|稱|指出|获悉|"
    r"消息|方面|，|。|、|；|;|\s|$)",
    re.IGNORECASE,
)


# Nominalised/reported propositions are mentions of an assertion, not direct
# issuer assertions. The relation owner applies this only to the same observed
# clause after its predicate; it never scans a later sentence for negation.
REPORTED_PROPOSITION_TAIL = re.compile(
    r"的(?:说法|传闻|报道|指控|观点|表述)|"
    r"(?:是|属于)[^，。；;!?]{0,24}?(?:的)?(?:说法|传闻|报道|指控|观点|表述)|"
    r"\b(?:claim|allegation|rumou?r|assertion)\s+(?:is|was|remains)\b",
    re.IGNORECASE,
)
POSSESSIVE_LINK = re.compile(r"^\s*(?:的|之|['’]s\b)", re.IGNORECASE)

# Direct product actions reuse actor/modifier/product ownership from this
# module. Actor capture prevents a nominal "discussed the launch" from being
# mistaken for an asserted launch; objects are validated by the shared head
# grammar in the relation binder.
_DIRECT_ACTION_ACTOR = (rf"(?:{ISSUER_WORD.pattern}|"
    rf"(?:(?:the|our|a)\s+)?(?:{RELATED_PARTY.pattern}|{THIRD_PARTY.pattern}))")
PRODUCT_LAUNCH_EN = re.compile(
    rf"(?P<actor>{_DIRECT_ACTION_ACTOR})"
    rf"(?P<qual>(?:\s+(?:{MODIFIER_TOKENS.pattern})){{0,6}})\s+"
    r"(?P<pred>launch(?:es|ed)?)\b(?P<obj>\s+(?:[A-Za-z][\w'&\-]*\s*){1,10})",
    re.IGNORECASE)
LAUNCH_OBJECT_END = re.compile(r"\b(?:for|to|with|at|in|on|during|but|and|which)\b", re.I)
SHIPMENT_DESTINATION = re.compile(
    rf"(?P<actor>{_DIRECT_ACTION_ACTOR})\s*"
    rf"(?P<qual>(?:(?:{_ABSENCE}|已经|已|开始|即将|将会|计划|拟)\s*)?"
    rf"(?:将)?(?:{ACTION_TEMPORAL_FRAME.pattern})\s*(?:将|把)|"
    rf"(?:{_ABSENCE}|已经|已|开始|即将|将会|计划|拟)(?:将|把)|"
    rf"将(?=\s*(?:[A-Za-z0-9]|{PRODUCT_SUFFIX.pattern.removesuffix('$')})))?"
    r"(?:(?:用于|用於)(?P<use>[\w㐀-鿿（）()\- ]{1,64}?)的)?"
    r"(?P<obj>[\w㐀-鿿（）()\- ]{1,48}?)\s*"
    rf"(?P<qual2>{_ABSENCE}|已经|已|开始|即将|将会|计划|拟)?"
    r"(?P<pred>发往|發往)"
    r"(?P<partner>[\w㐀-鿿（）()\- ]{1,48}?)"
    r"(?=(?:进行|進行|开展|開展)?(?:验证|驗證|认证|認證|测试|測試)|[。；;!?，,]|$)"
    r"(?:(?:进行|進行|开展|開展)?(?:验证|驗證|认证|認證|测试|測試))?",
    re.I)
PURPOSE_NAMED_OBJECT = re.compile(r"[A-Z][A-Za-z0-9&./+\-]*(?:\s+[A-Z][A-Za-z0-9&./+\-]*){0,3}")

EVENT_PATTERNS = (
    ("uncertain", UNCERTAIN_SCOPE),
    ("uncertain", UNCERTAIN_EN),
    ("double_negation", DOUBLE_NEGATION),
    ("approval_restricted", APPROVAL_RESTRICTED),
    ("qualification_pending_en", QUALIFICATION_PENDING_EN),
    ("qualification_pending", QUALIFICATION_PENDING),
    ("qualification_result", QUALIFICATION_RESULT),
    ("qualification_verb", QUALIFICATION_VERB),
    ("qualification_en", QUALIFICATION_EN),
    ("unsuccessful_validation", UNSUCCESSFUL_VALIDATION),
    ("commercialization", COMMERCIALIZATION),
    ("commercialization_en", COMMERCIALIZATION_EN),
    ("product_launch_en", PRODUCT_LAUNCH_EN),
    ("commercial_plan_en", COMMERCIAL_PLAN_EN),
    ("production_negation", PRODUCTION_NEGATION),
    ("production_suspend", PRODUCTION_SUSPEND),
    ("production_stop_action", PRODUCTION_STOP_ACTION),
    ("production_stop", PRODUCTION_STOP),
    ("production_aspect", PRODUCTION_ASPECT),
    ("production_en", PRODUCTION_EN),
    ("production_en_suspend", PRODUCTION_EN_SUSPEND),
    ("shipment_destination", SHIPMENT_DESTINATION),
    ("shipment", SHIPMENT),
    ("shipment_en", SHIPMENT_EN),
    ("scope_cn", SCOPE_CN),
    ("scope_en", SCOPE_EN),
    ("relation_contact", RELATION_CONTACT),
    ("relation_contact_en", RELATION_CONTACT_EN),
    ("relation_sign", RELATION_SIGN),
    ("relation_sign_en", RELATION_SIGN_EN),
    ("relation_intended", RELATION_INTENDED),
    ("relation_intended_en", RELATION_INTENDED_EN),
    ("relation_plan", RELATION_PLAN),
    ("relation_plan_en", RELATION_PLAN_EN),
)
