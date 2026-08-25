#!/usr/bin/env python3
"""Render help.html from data/resources.csv.

Why a build step on a site with no build step: the audience for this page is
somebody on an old phone, on transit data, possibly with a screen reader, and
possibly with JavaScript blocked by a locked-down library terminal. Fetching a
JSON file and templating every row in the browser fails all four of those. So
the rows are baked into the HTML here, once, and the browser's only job is to
hide the ones that do not match. The page works with JS off; it just shows
everything.

Run after editing data/resources.csv:  python3 build_help.py
"""

import csv
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent
CSV = ROOT / "data" / "resources.csv"
OUT = ROOT / "help.html"


# --------------------------------------------------------------- the needs
# Residents do not arrive looking for "Multi-Service / Navigation". They arrive
# with a sentence. These are those sentences, in the order somebody in trouble
# would scan them: the things that get people hurt first, then the rest.
#
# `cats` is the resource categories that land here. `also` is a second pass by
# subcategory keyword, because some resources genuinely answer two different
# sentences — a health-insurance helpline is both "seeing a doctor" and "this
# bill". A resource may appear under several needs; that is correct, and it is
# what stops somebody bouncing off the one heading we happened to file it under.
NEEDS = [
    {
        "key": "safety",
        "label": "I'm not safe where I live",
        "blurb": "Hurt or threatened by someone at home, or by a partner.",
        "icon": "shield",
        "cats": ["Domestic & Gender-Based Violence"],
    },
    {
        "key": "crisis",
        "label": "I'm in crisis, or I need someone to talk to",
        "blurb": "Feeling unsafe with yourself, overwhelmed, or struggling with drinking or drugs.",
        "icon": "heart",
        "cats": ["Mental Health & Substance Use"],
    },
    {
        "key": "food",
        "label": "I need food",
        "blurb": "Pantries, hot meals, and help signing up for food stamps (SNAP).",
        "icon": "bowl",
        "cats": ["Food & Nutrition"],
    },
    {
        "key": "housing",
        "label": "I need somewhere to stay, or I might lose my home",
        "blurb": "Shelter tonight, eviction help, and affordable housing.",
        "icon": "roof",
        "cats": ["Housing & Shelter"],
    },
    {
        "key": "bills",
        "label": "I got a medical bill, or my insurance said no",
        "blurb": "The free experts who handle hospital bills, denials, and prescription costs.",
        "icon": "bill",
        # These four sit in their own category because they answer a different
        # question from "I need to see a doctor". The site's whole public
        # identity is medical bills and denied claims, and before they were
        # added the directory held nothing at all on charity care, external
        # appeals, medical debt or surprise billing — the home page named four
        # doors and the list could open two of them.
        "cats": ["Medical Bills & Insurance"],
        "also": [
            "health insurance",
            "medicare help",
            "medication",
            "health access program",
            "free financial counseling",
        ],
    },
    {
        "key": "doctor",
        "label": "I need to see a doctor or a dentist",
        "blurb": "Clinics that see you whether or not you have insurance or papers.",
        "icon": "cross",
        "cats": ["Healthcare"],
    },
    {
        "key": "legal",
        "label": "I need a lawyer, or I have an immigration question",
        "blurb": "Free legal help — housing, immigration, benefits, and more.",
        "icon": "scale",
        "cats": ["Legal & Immigration"],
    },
    {
        "key": "money",
        "label": "I need help paying for things",
        "blurb": "Cash assistance, the heating bill, free tax filing, and benefits.",
        "icon": "wallet",
        "cats": ["Benefits & Financial Assistance"],
    },
    {
        "key": "family",
        "label": "I need help with my kids, or I'm a young person alone",
        "blurb": "Childcare, youth drop-in centers, and shelter for young people.",
        "icon": "family",
        "cats": ["Youth & Family"],
    },
    {
        "key": "senior",
        "label": "I'm an older adult, or I care for one",
        "blurb": "Meals, centers, and help for older New Yorkers.",
        "icon": "senior",
        "cats": ["Senior Services"],
    },
    {
        "key": "clothes",
        "label": "I need clothes, a coat, or baby supplies",
        "blurb": "Free clothing, winter coats, diapers, and children's gear.",
        "icon": "coat",
        "cats": ["Clothing & Supplies"],
    },
    {
        "key": "work",
        "label": "I need a job, or classes",
        "blurb": "Job training, paid work for young people, and English classes.",
        "icon": "work",
        "cats": ["Employment & Workforce"],
    },
    {
        "key": "getting-there",
        "label": "I need help getting there",
        "blurb": "Half-price MetroCard, rides to medical appointments, and Access-A-Ride.",
        "icon": "bus",
        "cats": ["Transportation"],
    },
    {
        "key": "veterans",
        "label": "I served in the military",
        "blurb": "Health care and services for veterans.",
        "icon": "star",
        "cats": ["Veterans"],
    },
    {
        "key": "disability",
        "label": "I have a disability, or I care for someone who does",
        "blurb": "Benefits, getting around, accessible housing, and being turned down.",
        "icon": "access",
        "cats": ["Disability"],
        # Disability cuts across everything, so this page is mostly built out
        # of resources filed elsewhere. That is the point: the person looking
        # for it should not have to know that Access-A-Ride is "transport" and
        # the rent freeze is "senior services".
        "also": [
            "paratransit", "access-a-ride", "disabilit", "disabled",
            "blind", "deaf", "low vision", "ssi", "home care", "special education",
        ],
    },
    {
        "key": "record",
        "label": "I have a criminal record, or I'm coming home",
        "blurb": "Jobs, housing, and legal help after jail or prison.",
        "icon": "gate",
        "cats": ["Reentry & Criminal Record"],
        "also": ["criminal record"],
    },
    {
        "key": "start",
        "label": "I'm not sure where to start",
        "blurb": "One phone number, or one website, that points you to everything else.",
        "icon": "compass",
        "cats": ["Multi-Service / Navigation"],
    },
]

# ------------------------------------------------------------- page copy
# Each need also gets its own page, so each need needs its own voice: a short
# name for a chip and a breadcrumb, a title split into the roman half and the
# gold italic half the way every heading on this site is, a sentence of intro,
# a search placeholder with words somebody would actually type, and a meta
# description.
#
# Reading level is checked in check.py. Two rules the copy must not break: it
# never states who qualifies for anything, and it never quotes a deadline.
COPY = {
    "safety": dict(
        short="Not safe at home",
        h1a="I'm not safe", h1b="where I live.",
        intro="If someone at home or a partner is hurting you, frightening you, or "
              "controlling you, these are the people to call. They answer at any hour, "
              "they do not need your name, and they do not ask about immigration status.",
        ph="Try: shelter, hotline, lawyer",
        seo="Free help in New York City for domestic and gender-based violence: "
            "24-hour hotlines, Family Justice Centers, safe shelter and free lawyers. "
            "No immigration status asked."),
    "crisis": dict(
        short="Crisis & mental health",
        h1a="I'm in crisis, or I need", h1b="someone to talk to.",
        intro="If you feel unsafe with yourself, cannot cope, or are struggling with "
              "drinking or drugs, someone is awake and trained to talk with you right "
              "now. Calling is free and you do not have to give your name.",
        ph="Try: someone to talk to, rehab",
        seo="Free mental health and substance use help in New York City: 24-hour crisis "
            "lines, counseling, treatment referral, overdose prevention, and support for "
            "young and LGBTQ+ New Yorkers."),
    "food": dict(
        short="Food",
        h1a="I need", h1b="food.",
        intro="Food pantries, hot meals you can walk into, groceries, and help signing "
              "up for SNAP — what most people still call food stamps. Nearly all of it "
              "is free, and most of it does not ask about immigration status.",
        ph="Try: pantry, food stamps, meal",
        seo="Free food in New York City: food pantries, soup kitchens, groceries, SNAP "
            "and WIC sign-up help, and meals delivered to people who cannot leave home."),
    "housing": dict(
        short="Housing & shelter",
        h1a="I need somewhere to stay, or", h1b="I might lose my home.",
        intro="Shelter for tonight. Help stopping an eviction. Money toward rent "
              "you have fallen behind on. And the free lawyers New York gives "
              "tenants. If you have a court paper about your apartment, call "
              "somebody on this page today.",
        ph="Try: shelter, eviction, rent",
        seo="Free housing help in New York City: shelter intake, eviction prevention, "
            "free tenant lawyers, emergency rent money, and affordable housing."),
    "bills": dict(
        short="Medical bills",
        h1a="I got a medical bill, or", h1b="my insurance said no.",
        intro="This is the help Waypoint exists to carry to people. Every hospital in "
              "New York has to offer financial assistance. The state hears appeals when "
              "an insurer says no. Free counselors take these cases in dozens of "
              "languages. Almost nobody who qualifies ever finds out.",
        ph="Try: hospital bill, denied claim",
        seo="Free help with medical bills and denied insurance claims in New York City: "
            "hospital charity care, external appeals, prescription costs, medical debt, "
            "and free expert counselors."),
    "doctor": dict(
        short="A doctor or dentist",
        h1a="I need to see", h1b="a doctor or a dentist.",
        intro="Clinics that see you whether or not you have insurance, and whether or "
              "not you have papers. Many charge on a sliding scale, which means the "
              "price depends on what you earn — and some charge nothing.",
        ph="Try: clinic, dentist, insurance",
        seo="Low-cost and free health care in New York City: community clinics, dental "
            "and vision care, sexual and reproductive health, and HIV care. Most do not "
            "ask about immigration status."),
    "legal": dict(
        short="A lawyer",
        h1a="I need a lawyer, or I have", h1b="an immigration question.",
        intro="Free lawyers for the problems that get people hurt: eviction, "
              "immigration, benefits that were cut off, wages that were not paid, "
              "safety at home. None of these charge, and none of them are notarios.",
        ph="Try: eviction, immigration, wages",
        seo="Free legal help in New York City: housing and eviction, immigration and "
            "deportation defense, benefits, wages, and family safety. Free, and not "
            "notarios."),
    "money": dict(
        short="Paying for things",
        h1a="I need help", h1b="paying for things.",
        intro="Cash assistance, the heating and electric bill, free tax filing that "
              "gets people thousands of dollars they were owed, and someone to sit down "
              "with you about debt. All of it free.",
        ph="Try: con ed, cash, free tax help",
        seo="Free help with money in New York City: cash assistance, heating and utility "
            "bills, free tax preparation, health insurance, and free financial "
            "counseling."),
    "family": dict(
        short="Kids & young people",
        h1a="I need help with my kids, or", h1b="I'm a young person alone.",
        intro="Free childcare and early learning, support for parents, and safe places "
              "for young people who have nowhere to sleep. If you are under 25 and on "
              "the street tonight, the youth shelters here are for you.",
        ph="Try: daycare, youth shelter",
        seo="Free help for children, parents and young people in New York City: "
            "childcare and pre-K, family support, youth drop-in centers, and shelter "
            "for young people."),
    "senior": dict(
        short="Older adults",
        h1a="I'm an older adult,", h1b="or I care for one.",
        intro="Meals. Centres where there are people to talk to. Help with "
              "Medicare and with the rent. And someone to call if an older person "
              "is being harmed, or taken advantage of.",
        ph="Try: meals, senior center, medicare",
        seo="Free help for older New Yorkers: meals and Citymeals, senior centers, "
            "Medicare and rent help, and protection for adults at risk."),
    "clothes": dict(
        short="Clothes & supplies",
        h1a="I need clothes, a coat,", h1b="or baby supplies.",
        intro="Winter coats, everyday clothes, diapers, cribs and children's gear, and "
              "an interview outfit if you have one coming up. Free, and nobody asks why "
              "you need it.",
        ph="Try: coat, diapers, interview",
        seo="Free clothing and supplies in New York City: winter coats, everyday "
            "clothes, diapers and baby gear, and free interview outfits."),
    "work": dict(
        short="A job, or classes",
        h1a="I need", h1b="a job, or classes.",
        intro="Free job training and placement, paid summer work for young people, "
              "English classes, and finishing a high school diploma as an adult. None "
              "of these charge tuition.",
        ph="Try: job training, english, ged",
        seo="Free job training, employment help and adult classes in New York City: "
            "Workforce1 centers, paid youth jobs, free English classes, and high school "
            "equivalency."),
    "getting-there": dict(
        short="Getting there",
        h1a="I need help", h1b="getting there.",
        intro="Half-price MetroCards, if you do not earn much. Rides to medical "
              "appointments. And Access-A-Ride, for when the subway and the bus "
              "are not possible for you.",
        ph="Try: fair fares, access-a-ride",
        seo="Help getting around New York City on a low income: Fair Fares half-price "
            "MetroCards, reduced fares, Access-A-Ride, and free rides to medical "
            "appointments."),
    "veterans": dict(
        short="Veterans",
        h1a="I served", h1b="in the military.",
        intro="Health care, benefits, housing and a crisis line, for people who served "
              "and for their families. You do not need a discharge of any particular "
              "kind to call and ask.",
        ph="Try: va clinic, benefits, crisis",
        seo="Free help for veterans in New York City: health care, benefits navigation, "
            "housing, and the Veterans Crisis Line."),
    "disability": dict(
        short="Disability",
        h1a="I have a disability,", h1b="or I care for someone who does.",
        intro="Benefits, and how to keep them. Getting around a city that was "
              "not built for you. Care at home, and somewhere to live. And what "
              "to do when a service is cut off, or when somebody refuses to make "
              "a change you need.",
        ph="Try: ssi, access-a-ride, home care",
        seo="Free help for disabled New Yorkers: benefits and appeals, Access-A-Ride "
            "and reduced fares, accessible and supportive housing, care at home, "
            "vision and hearing services, and the City's disability office."),
    "record": dict(
        short="After jail or prison",
        h1a="I have a criminal record,", h1b="or I'm coming home.",
        intro="A record follows people into every job application and every "
              "apartment viewing. New York has organisations that exist for "
              "exactly that. Jobs that start within days. Housing. Health care. "
              "And lawyers who seal records, and who take on the people who turn "
              "you down for one.",
        ph="Try: job, seal my record, housing",
        seo="Free reentry help in New York City after jail or prison: paid "
            "transitional jobs, housing, health care, family support, and lawyers "
            "who handle record sealing and discrimination."),
    "start": dict(
        short="Not sure where to start",
        h1a="I'm not sure", h1b="where to start.",
        intro="If you do not know what to ask for, start here. One phone number, or one "
              "website, that will listen to your situation and point you at the right "
              "thing — in your language, at any hour, without asking about immigration "
              "status.",
        ph="Try: what do i qualify for",
        seo="Not sure where to start? New York City's free information and referral "
            "lines, benefit screeners, and directories — in any language, at any hour."),
}

# One apostrophe, everywhere. The narrative page sets "I'm not safe where I
# live" with a typographic apostrophe because that is what prose does; the
# directory was setting the same sentence with a typewriter one, and the two
# halves of the site were quietly using different punctuation for the same
# words. Normalised at the source rather than at each call site, so it holds
# for anything added later — and never applied to a URL, where an apostrophe
# is a character and not a quotation mark.
CURLY = str.maketrans({"'": "\u2019"})


def prose(s):
    return (s or "").translate(CURLY)


# ------------------------------------------------- the words in ten languages
# The page offers ten languages and, until this table existed, could be read in
# ten and searched in one. Somebody who opened the Spanish panel, understood
# it, and then typed "comida" into the box got nothing.
#
# So every resource under a need also matches the words somebody would type for
# that need in each of the ten. These are queries, not translations: short,
# concrete, the noun a person reaches for. They are attached to rows rather
# than translated into the interface, which means no page has to be duplicated
# and a search in Bengali lands on exactly the same resource an English search
# would.
#
# help.js matches a non-ASCII term as a plain substring, because \b is defined
# by ASCII word characters and means nothing in Chinese or Arabic.
NEED_WORDS = {
    "food": [
        "comida alimentos despensa hambre comer cupones de alimentos",
        "食物 食品 免费食物 食物救济 粮食券 吃饭",
        "еда продукты питание талоны на еду голод",
        "খাবার খাদ্য বিনামূল্যে খাবার",
        "manje manje gratis grangou",
        "음식 식품 무료급식 푸드뱅크",
        "طعام غذاء بنك الطعام مساعدة غذائية",
        "کھانا خوراک مفت کھانا",
        "nourriture alimentation banque alimentaire manger",
        "jedzenie żywność bank żywności",
    ],
    "doctor": [
        "médico doctor clínica dentista salud sin seguro",
        "医生 看病 诊所 牙医 医疗 免费诊所",
        "врач доктор клиника стоматолог здоровье",
        "ডাক্তার চিকিৎসা ক্লিনিক দাঁতের ডাক্তার",
        "doktè dantis klinik sante",
        "의사 병원 치과 진료 무료진료",
        "طبيب عيادة أسنان رعاية صحية",
        "ڈاکٹر علاج کلینک دانتوں کا ڈاکٹر",
        "médecin clinique dentiste santé",
        "lekarz przychodnia dentysta zdrowie",
    ],
    "bills": [
        "factura médica cuenta del hospital seguro deuda médica negaron",
        "医疗账单 医院账单 保险 拒赔 医疗债务",
        "счёт за лечение медицинский счёт страховка отказ",
        "চিকিৎসার বিল হাসপাতালের বিল বীমা",
        "bòdwo medikal bòdwo lopital asirans",
        "의료비 병원비 보험 거절 의료비청구서",
        "فاتورة طبية فاتورة المستشفى تأمين رفض",
        "طبی بل ہسپتال کا بل انشورنس",
        "facture médicale hôpital assurance refus",
        "rachunek za leczenie szpital ubezpieczenie",
    ],
    "housing": [
        "vivienda renta alquiler desalojo refugio albergue sin hogar",
        "住房 房租 驱逐 庇护所 收容所 无家可归",
        "жильё аренда выселение приют бездомный",
        "বাসস্থান বাড়ি ভাড়া উচ্ছেদ আশ্রয়",
        "lojman kay lwaye degèpi abri",
        "주거 집세 퇴거 쉼터 노숙",
        "سكن إيجار إخلاء مأوى تشرد",
        "رہائش کرایہ بے دخلی پناہ",
        "logement loyer expulsion hébergement sans-abri",
        "mieszkanie czynsz eksmisja schronisko bezdomny",
    ],
    "legal": [
        "abogado ayuda legal inmigración deportación derechos",
        "律师 法律援助 移民 遣返 权利",
        "адвокат юрист иммиграция депортация права",
        "আইনজীবী আইনি সাহায্য অভিবাসন",
        "avoka èd legal imigrasyon depòtasyon",
        "변호사 법률지원 이민 추방",
        "محامي مساعدة قانونية هجرة ترحيل",
        "وکیل قانونی مدد امیگریشن",
        "avocat aide juridique immigration expulsion",
        "prawnik pomoc prawna imigracja deportacja",
    ],
    "safety": [
        "violencia doméstica maltrato abuso orden de protección golpea",
        "家庭暴力 虐待 保护令 打我",
        "домашнее насилие побои жестокое обращение",
        "পারিবারিক সহিংসতা নির্যাতন",
        "vyolans lakay abi bat mwen",
        "가정폭력 학대 접근금지",
        "عنف أسري إساءة أمر حماية يضربني",
        "گھریلو تشدد زیادتی مارتا ہے",
        "violence conjugale maltraitance ordonnance de protection",
        "przemoc domowa znęcanie",
    ],
    "crisis": [
        "crisis suicidio ayuda emocional drogas alcohol adicción",
        "危机 自杀 心理健康 毒品 酗酒 成瘾",
        "кризис суицид психическое здоровье наркотики алкоголь",
        "আত্মহত্যা মানসিক স্বাস্থ্য মাদক",
        "kriz swisid sante mantal dwòg",
        "자살 정신건강 위기 중독 마약",
        "أزمة انتحار صحة نفسية إدمان مخدرات",
        "خودکشی ذہنی صحت نشہ",
        "crise suicide santé mentale drogue alcool",
        "kryzys samobójstwo zdrowie psychiczne uzależnienie",
    ],
    "money": [
        "dinero ayuda económica efectivo luz gas impuestos beneficios",
        "现金补助 经济援助 电费 报税 福利",
        "деньги пособие счета налоги льготы",
        "আর্থিক সাহায্য নগদ কর",
        "lajan èd ekonomik kouran taks",
        "현금지원 공과금 세금 복지",
        "مساعدة مالية فواتير ضرائب إعانة",
        "مالی مدد بل ٹیکس",
        "aide financière factures impôts allocations",
        "pomoc finansowa rachunki podatki zasiłek",
    ],
    "family": [
        "niños guardería cuidado infantil hijos escuela",
        "儿童 托儿 幼儿园 孩子 课后",
        "дети детский сад ребёнок",
        "শিশু ডে কেয়ার সন্তান",
        "timoun gadri pitit",
        "아이 어린이집 보육 방과후",
        "أطفال حضانة رعاية الطفل",
        "بچے ڈے کیئر بچوں کی دیکھ بھال",
        "enfants garderie crèche",
        "dzieci żłobek przedszkole opieka",
    ],
    "senior": [
        "personas mayores ancianos tercera edad jubilados",
        "长者 老人 老年人 安老",
        "пожилые пенсионеры престарелые",
        "প্রবীণ বয়স্ক",
        "granmoun aje",
        "어르신 노인 경로",
        "كبار السن مسنين رعاية المسنين",
        "بزرگ عمر رسیدہ",
        "personnes âgées aînés retraités",
        "seniorzy osoby starsze emeryci",
    ],
    "clothes": [
        "ropa abrigo pañales cosas de bebé",
        "衣服 外套 尿布 婴儿用品",
        "одежда куртка подгузники",
        "জামাকাপড় কোট ডায়াপার",
        "rad manto kouchèt",
        "옷 외투 기저귀",
        "ملابس معطف حفاضات",
        "کپڑے کوٹ ڈائپر",
        "vêtements manteau couches",
        "ubrania kurtka pieluchy",
    ],
    "work": [
        "trabajo empleo clases de inglés capacitación",
        "工作 就业 英语课 职业培训",
        "работа трудоустройство курсы английского",
        "কাজ চাকরি ইংরেজি ক্লাস",
        "travay djòb kou anglè",
        "일자리 취업 영어수업 직업훈련",
        "عمل وظيفة دروس إنجليزية تدريب",
        "نوکری کام انگریزی کلاس",
        "emploi travail cours d'anglais formation",
        "praca zatrudnienie kursy angielskiego",
    ],
    "getting-there": [
        "transporte metrocard pasaje viaje al médico",
        "交通 地铁卡 车费 就医交通",
        "транспорт проезд метрокарта",
        "যাতায়াত পরিবহন",
        "transpò kat metro",
        "교통 지하철 교통비",
        "مواصلات نقل بطاقة المترو",
        "سفر ٹرانسپورٹ",
        "transport métro déplacement",
        "transport przejazd metro",
    ],
    "veterans": [
        "veterano militar ejército",
        "退伍军人 军人",
        "ветеран военнослужащий",
        "প্রাক্তন সৈনিক",
        "veteran lame",
        "재향군인 참전용사",
        "محارب قديم جندي",
        "سابق فوجی",
        "ancien combattant vétéran armée",
        "weteran wojsko",
    ],
    "disability": [
        "discapacidad silla de ruedas ciego sordo incapacidad",
        "残疾 轮椅 失明 聋 残障",
        "инвалидность коляска слепой глухой",
        "প্রতিবন্ধী অক্ষমতা",
        "andikap chèz woulant avèg soud",
        "장애 휠체어 시각장애 청각장애",
        "إعاقة كرسي متحرك أعمى أصم",
        "معذوری وہیل چیئر نابینا بہرا",
        "handicap fauteuil roulant aveugle sourd",
        "niepełnosprawność wózek niewidomy głuchy",
    ],
    "record": [
        "antecedentes penales salir de prisión cárcel condena",
        "犯罪记录 出狱 监狱 前科",
        "судимость тюрьма освобождение",
        "জেল অপরাধের রেকর্ড",
        "prizon kazye jidisyè",
        "전과 출소 교도소",
        "سجل جنائي سجن الإفراج",
        "جیل مجرمانہ ریکارڈ",
        "casier judiciaire prison sortie de prison",
        "wyrok więzienie karalność",
    ],
    "start": [
        "no sé por dónde empezar ayuda información recursos",
        "不知道从哪开始 帮助 资源 咨询",
        "не знаю с чего начать помощь информация",
        "সাহায্য তথ্য",
        "èd enfòmasyon ki kote pou kòmanse",
        "도움 정보 어디서 시작",
        "مساعدة معلومات من أين أبدأ",
        "مدد معلومات",
        "aide information par où commencer",
        "pomoc informacja od czego zacząć",
    ],
}

for _k, _v in NEED_WORDS.items():
    if len(_v) != 10:
        raise SystemExit(f"NEED_WORDS[{_k!r}] has {len(_v)} language(s), expected 10")



for _need in NEEDS:
    if _need["key"] not in NEED_WORDS:
        raise SystemExit(f'{_need["key"]}: no NEED_WORDS, so this kind of help '
                         'cannot be searched for in any language but English')
    _need.update(COPY[_need["key"]])
    for _f in ("label", "blurb", "short", "h1a", "h1b", "intro", "ph", "seo"):
        _need[_f] = prose(_need[_f])
assert set(COPY) == {n["key"] for n in NEEDS}, "COPY and NEEDS disagree"


# ------------------------------------------------------------- the groups
# Second level. A need with forty places under it is a wall; a need broken
# into "somewhere to sleep tonight / stop an eviction / money for the rent" is
# a page somebody can skim in ten seconds and leave with a phone number.
#
# The CSV's own Subcategory column cannot do this job: it is free text and
# nearly every value is unique (118 rows carried 96 distinct subcategories),
# so grouping by it produces groups of one. These are curated buckets instead,
# matched against the row's subcategory, tags and name, in order — first rule
# that fires wins, so put the specific rules above the general ones.
#
# A row that matches nothing lands in the need's final bucket, and the build
# prints how many did, so a bucket quietly swallowing half a category shows up
# the moment it happens rather than six months later.
GROUPS = {
    "safety": [
        ("now",       "Talk to someone right now",
         ["hotline", "crisis", "24-hour", "24/7"]),
        ("centers",   "Walk in, or somewhere safe to sleep",
         ["center", "shelter", "one-stop", "residential", "safe house"]),
        ("traffick",  "If someone is controlling your work or your papers",
         ["traffick"]),
        ("young",     "If you are young",
         ["young", "dating", "youth", "teen"]),
        ("counsel",   "Counseling, and someone to keep talking to",
         ["counsel", "therapy", "response", "treatment", "advocacy"]),
        ("legal",     "A lawyer, an order of protection, money owed to you",
         ["legal", "court", "order of protection", "immigration",
          "compensation", "victim services"]),
        ("community", "Help in your language, or from your community",
         ["asian", "latina", "arab", "lgbtq", "jewish", "african", "community",
          "south asian", "chinese", "disabled"]),
        ("more",      "More places that help", []),
    ],
    "crisis": [
        ("young",     "For young people and LGBTQ+ people",
         ["youth", "lgbtq", "trans", "queer", "trevor"]),
        ("now",       "Call or text right now",
         ["crisis", "hotline", "lifeline", "text crisis", "warmline", "988"]),
        ("using",     "Drinking, drugs, and overdose",
         ["addiction", "substance", "overdose", "treatment", "harm reduction",
          "recovery", "alcohol", "opioid"]),
        ("ongoing",   "Someone to keep talking to",
         ["counsel", "therapy", "peer", "support", "clubhouse", "navigation"]),
        ("more",      "More places that help", []),
    ],
    "food": [
        ("today",     "Find food near you today",
         ["locator", "reservation", "find", "map", "emergency food"]),
        ("pantry",    "Pantries and groceries",
         ["pantry", "grocer", "food network", "customer-choice", "kosher"]),
        ("delivered", "Meals brought to you",
         ["homebound", "delivered", "cooked for an illness", "citymeals"]),
        ("meals",     "Hot meals you can walk into",
         ["soup kitchen", "meals", "hot meal", "community kitchen"]),
        ("snap",      "SNAP, WIC, and school meals",
         ["snap", "wic", "money for groceries", "food for pregnancy",
          "school meal", "nutrition"]),
        ("more",      "More places that help", []),
    ],
    "housing": [
        ("tonight",   "Somewhere to sleep tonight",
         ["shelter", "intake", "emergency shelter", "drop-in", "safe haven"]),
        ("eviction",  "Stop an eviction, or a landlord problem",
         ["eviction", "tenant", "housing court", "landlord", "lockout", "repairs"]),
        ("money",     "Money for the rent or the arrears",
         ["arrears", "cash", "one shot", "rent", "voucher", "emergency cash"]),
        ("permanent", "Finding somewhere permanent",
         ["affordable", "lottery", "nycha", "section 8", "supportive housing"]),
        ("street",    "If you are sleeping on the street",
         ["street", "outreach", "homeless services", "unsheltered"]),
        ("more",      "More places that help", []),
    ],
    "bills": [
        ("start",     "The free experts who take these cases",
         ["medical bills", "denied claims", "consumer assistance", "advocate",
          "health insurance help", "helpline"]),
        ("charity",   "Getting a hospital bill reduced or wiped out",
         ["charity care", "financial assistance", "hospital bill", "medical debt",
          "financial counsel"]),
        ("appeal",    "Fighting a denial or an insurance decision",
         ["denial", "appeal", "external review", "grievance", "complaint",
          "surprise bill"]),
        ("rx",        "Paying for prescriptions",
         ["medication", "medicine", "prescription", "pharmac", "copay",
          "co-pay", "drug"]),
        ("cover",     "Getting covered in the first place",
         ["signing up", "enrollment", "medicaid", "medicare", "marketplace",
          "health insurance", "a way in without insurance"]),
        ("more",      "More places that help", []),
    ],
    "doctor": [
        # Specific before general, always: a rule matches the row's tags as
        # well as its subcategory, so "dental" has to get its chance before
        # "clinic" does or every dental clinic files itself under clinics.
        ("dental",    "Teeth",
         ["dental", "dentist"]),
        ("eyes",      "Eyes and glasses",
         ["vision", "eye care", "optical", "glasses", "optometry"]),
        ("sexual",    "Sexual and reproductive health",
         ["sexual", "reproductive", "planned parenthood", "std", "sti",
          "birth control", "family planning"]),
        ("hiv",       "HIV care and prevention",
         ["hiv", "aids", "prep"]),
        ("women",     "Pregnancy and new parents",
         ["maternal", "doula", "prenatal", "newborn", "pregnan"]),
        ("homeless",  "If you have nowhere to live",
         ["care for homeless", "homeless"]),
        ("start",     "The citywide networks",
         ["a way in without insurance", "public hospitals", "find a clinic",
          "nowhere to live"]),
        ("clinic",    "Neighbourhood health centres, across the city",
         ["fqhc", "clinic", "health cent", "primary care", "medical care"]),
        ("rx",        "Help paying for a prescription",
         ["medication", "medicine", "prescription", "pharmac"]),
        ("more",      "More clinics and programs", []),
    ],
    "legal": [
        ("any",       "Free lawyers for almost anything",
         ["free civil", "free lawyers", "legal hotline", "civil legal",
          "find a free lawyer", "legal services", "everything around a case"]),
        ("immigration", "Immigration",
         ["immigra", "deportation", "detained", "asylum", "citizenship",
          "daca", "undocument", "newly arrived"]),
        ("housing",   "Housing, eviction, and landlords",
         ["tenant", "eviction", "housing"]),
        ("money",     "Benefits, debt, and consumer problems",
         ["benefit", "debt", "consumer", "wage", "employ", "unemployment"]),
        ("family",    "Family, safety, and criminal matters",
         ["family", "domestic", "criminal", "survivor", "child", "record",
          "discrimination"]),
        ("rights",    "Know your rights",
         ["know your rights", "rights"]),
        ("id",        "Names, IDs, and papers",
         ["name change", "trans", "gender", "id", "identification"]),
        ("more",      "More legal help", []),
    ],
    "money": [
        ("emergency", "After a fire, a flood, or a death",
         ["after a fire", "after a death", "disaster", "burial"]),
        ("cash",      "Cash assistance and income",
         ["income support", "cash assistance", "federal income", "ssi",
          "disability", "unemployment"]),
        ("utility",   "The heating, electric, or water bill",
         ["utility", "heating", "heap", "energy", "water", "con edison"]),
        ("tax",       "Taxes and the credits people miss",
         ["tax", "eitc", "credit"]),
        ("insurance", "Health insurance",
         ["health insurance", "medicare", "medicaid", "enrollment"]),
        ("coach",     "Someone to sit down with about money",
         ["financial counsel", "coach", "budget", "banking", "debt"]),
        ("more",      "More help with money", []),
    ],
    "family": [
        ("childcare", "Childcare and early learning",
         ["childcare", "child care", "early childhood", "head start", "pre-k",
          "3-k", "daycare"]),
        ("young",     "Young people alone, or on the street",
         ["youth shelter", "runaway", "youth outreach", "drop-in", "homeless youth",
          "lgbtq youth"]),
        ("support",   "Support for parents and families",
         ["family", "parent", "comprehensive youth", "home visiting"]),
        ("school",    "School, after school, and summer",
         ["school", "after school", "summer", "tutor", "education"]),
        ("more",      "More help for families", []),
    ],
    "senior": [
        ("start",     "One call to begin with",
         ["one call", "aging connect", "navigation"]),
        ("meals",     "Meals",
         ["meals", "homebound", "nutrition", "citymeals"]),
        ("centers",   "Centres, activities, and company",
         ["cent", "company", "at-home", "social", "activities"]),
        ("money",     "Money, rent, and benefits for older adults",
         ["scrie", "rent", "benefit", "medicare", "epic", "money"]),
        ("safety",    "If an older adult is being harmed",
         ["being harmed", "protection", "at-risk", "abuse", "elder"]),
        ("more",      "More help for older adults", []),
    ],
    "clothes": [
        ("work",      "Something to wear to an interview",
         ["interview", "professional attire", "career gear",
          "dress for success", "bottomless closet"]),
        ("baby",      "Babies and children",
         ["baby", "diaper", "children", "crib", "stroller", "gear"]),
        ("clothes",   "Clothes and winter coats",
         ["coat", "clothing", "thrift", "multi-service"]),
        ("more",      "More places for supplies", []),
    ],
    "work": [
        ("rights",    "Your rights at work",
         ["rights at work", "workers rights", "wage"]),
        ("jobs",      "Jobs and training",
         ["job search", "training", "workforce", "career", "apprentice"]),
        ("young",     "Paid work for young people",
         ["youth paid", "youth job", "summer youth", "syep"]),
        ("school",    "English classes and finishing school",
         ["esol", "adult education", "ged", "hse", "literacy", "english"]),
        ("more",      "More work and class programs", []),
    ],
    "getting-there": [
        ("fare",      "Cheaper subway and bus fares",
         ["half-price", "half-fare", "fair fares", "reduced fare",
          "cheaper fares", "discount"]),
        ("medical",   "Rides to medical appointments",
         ["medical", "appointment", "treatment"]),
        ("disability", "If you cannot use the subway or bus",
         ["paratransit", "access-a-ride", "disabilit", "ambulette"]),
        ("older",     "If you are over 60",
         ["older adults", "senior"]),
        ("more",      "More help getting there", []),
    ],
    "veterans": [
        ("crisis",    "If you are in crisis",
         ["crisis", "hotline"]),
        ("counsel",   "Someone to talk to",
         ["counseling", "counselling", "readjustment", "ptsd", "therapy"]),
        ("health",    "Health care",
         ["healthcare", "health care", "va "]),
        ("housing",   "Housing and money",
         ["housing", "benefits", "claiming", "jobs"]),
        ("start",     "Where to begin",
         ["where veterans start", "navigation", "veteran services"]),
        ("more",      "More veteran programs", []),
    ],
    "disability": [
        ("start",     "Where to begin",
         ["one call", "disability info"]),
        ("senses",    "Sight and hearing",
         ["blind", "deaf", "vision", "hearing", "optometry", "eyes"]),
        ("getting",   "Getting around",
         ["paratransit", "access-a-ride", "fare", "transit", "ride",
          "transportation", "ferry"]),
        ("home",      "Care at home, and somewhere to live",
         ["home care", "housing", "supportive", "family type", "shelter",
          "rent", "scrie", "drie"]),
        ("children",  "Children and school",
         ["children", "child", "special education", "early intervention",
          "youth", "childcare", "school"]),
        ("health",    "Health care",
         ["clinic", "fqhc", "health center", "dental", "hiv", "mental"]),
        ("centers",   "A centre run by disabled people, in your borough",
         ["disability benefits help", "independent living"]),
        ("legal",     "When a right is denied",
         ["disability legal", "legal", "discrimination", "rights"]),
        ("money",     "Benefits, and keeping them",
         ["benefits", "ssi", "income", "insurance", "medicaid", "medicare",
          "cash", "tax", "counsel"]),
        ("more",      "More programs", []),
    ],
    "record": [
        ("start",     "Where to begin",
         ["reentry services", "start-here"]),
        ("jobs",      "Work that will hire you",
         ["jobs after prison", "job", "employment", "training"]),
        ("legal",     "Sealing a record, and being turned down for one",
         ["legal", "discrimination", "criminal record", "sealing"]),
        ("school",    "School and college after a conviction",
         ["college", "education", "school", "degree"]),
        ("women",     "For women",
         ["women", "mothers"]),
        ("courts",    "Instead of a sentence",
         ["community court", "alternatives", "diversion", "justice"]),
        ("family",    "Family, health, and housing",
         ["family", "housing", "health", "treatment"]),
        ("more",      "More reentry programs", []),
    ],
    "start": [
        ("call",      "One call, any question",
         ["one call", "citywide info", "info & referral", "hotline", "311"]),
        ("check",     "Check what you already qualify for",
         ["check what you can get", "screener", "eligibility", "benefits"]),
        ("papers",    "Papers, ID, and proof",
         ["getting an id", "identification", "idnyc", "document",
          "birth certificate"]),
        # A settlement house does everything under one roof, which is exactly
        # the answer for somebody who cannot name what they need. Filing them
        # as "a directory to search" buried the most useful thing on the page —
        # and eighteen of them in one heading buried it again, so they are
        # split the way somebody would actually choose between them: by where
        # they are.
        # The first of these carries the meaning; the rest are read straight
        # after it and only have to say where. Repeating the whole phrase five
        # times made the rail three lines deep per entry on a phone.
        ("search",    "Search a directory yourself",
         ["search", "directory", "locator", "library", "find a free lawyer"]),
        ("onestop",   "One place that does everything", ["citywide"]),
        ("os-bronx",  "In the Bronx", ["bronx"]),
        ("os-bklyn",  "In Brooklyn", ["brooklyn"]),
        ("os-mnhtn",  "In Manhattan", ["manhattan"]),
        ("os-queens", "In Queens", ["queens"]),
        ("os-si",     "On Staten Island", ["staten-island"]),
        ("more",      "Other places that point the way", []),
    ],
}


# The tokens boroughs_for() produces, which is what a borough bucket matches.
BORO_WORDS = {"bronx", "brooklyn", "manhattan", "queens", "staten-island", "citywide"}

BOROUGHS = [
    ("bronx", "Bronx"),
    ("brooklyn", "Brooklyn"),
    ("manhattan", "Manhattan"),
    ("queens", "Queens"),
    ("staten-island", "Staten Island"),
]

# The ten languages are not a guess. New York City's Local Law 30 designates
# exactly these as the citywide languages every agency must translate into,
# ordered by how many people in the city speak them and do not speak English
# well: Spanish, Chinese, Russian, Bengali, Haitian Creole, Korean, Arabic,
# Urdu, French, Polish. This page holds all ten.
#
# `tag` is a real BCP-47 tag, not our internal key. A button reading "Español"
# marked lang="spanish" is marked with nothing — the tag is invalid, so a
# screen reader keeps its English voice and reads the label as English. On the
# one row of the page addressed to people who do not read English, that is not
# a detail. Chinese is tagged zh-Hans rather than zh because the text below is
# Simplified, and a renderer that guesses wrong picks the wrong glyph forms.
#
# ---------------------------------------------------------------------------
# TRANSLATION STATUS: NOT YET REVIEWED BY A NATIVE SPEAKER.
#
# These strings are deliberately short, plain, and free of anything a reader
# has to act on precisely: no eligibility rules, no deadlines, no promises.
# The only instructions any of them give are "call 911 if you are in danger",
# "call 988 to talk to somebody", and "call 311 and ask for an interpreter",
# all of which are true in every language and are the safe fallback if a
# sentence here reads badly. Get each one read by a speaker before this goes
# live; the obvious reviewers are the multilingual students the corps is
# recruiting.
#
# One rule these must not break: a phone number stays in Western digits, in
# every language. Bengali prose would normally write 311 as ৩১১, and Urdu as
# ۳۱۱ — both correct, and both useless on a keypad. The person has to match
# what they read against the buttons on the phone in their hand. check.py
# enforces this.
#
# `needs` is what makes this more than a notice. Every one of the sixteen
# kinds of help has its label here, so somebody who cannot read the English
# page can still choose what they need and land on the right page — which is
# the whole difference between "we acknowledge you exist" and "here is the
# thing you came for".
LANGUAGES = [
    {
        "key": "spanish", "endonym": "Español", "tag": "es", "dir": "ltr",
        "name_en": "Spanish",
        "title": "Ayuda gratuita en la ciudad de Nueva York",
        "body": "Esta página tiene una lista de lugares que dan comida, "
                "atención médica, ayuda con la vivienda, ayuda legal y ayuda "
                "económica. Casi todo es gratis. La mayoría de estos lugares "
                "no preguntan sobre su estatus migratorio.",
        "sos": "Si está en peligro, llame al 911. Para hablar con alguien a "
               "cualquier hora, llame al 988. Los dos son gratis.",
        "interp": "La lista está escrita en inglés. Llame al 311 y pida un "
                  "intérprete de español. Es gratis, a cualquier hora.",
        "search": "También puede escribir en español en el buscador. Por ejemplo: comida, abogado, vivienda.",
        "browse": "¿Qué necesita?",
        "cta": "Ver los lugares que atienden en español",
        "needs": {
            "safety": "No estoy seguro en mi casa",
            "crisis": "Estoy en crisis, o necesito hablar con alguien",
            "food": "Necesito comida",
            "housing": "Necesito dónde quedarme, o puedo perder mi vivienda",
            "bills": "Recibí una factura médica, o mi seguro dijo que no",
            "doctor": "Necesito ver a un médico o a un dentista",
            "legal": "Necesito un abogado, o tengo una pregunta de inmigración",
            "money": "Necesito ayuda para pagar cosas",
            "family": "Necesito ayuda con mis hijos, o soy joven y estoy solo",
            "senior": "Soy una persona mayor, o cuido a una",
            "clothes": "Necesito ropa, un abrigo o cosas para el bebé",
            "work": "Necesito trabajo, o clases",
            "getting-there": "Necesito ayuda para llegar",
            "veterans": "Serví en las fuerzas armadas",
            "disability": "Tengo una discapacidad, o cuido a alguien que la tiene",
            "record": "Tengo antecedentes penales, o estoy saliendo de prisión",
            "start": "No sé por dónde empezar",
        },
    },
    {
        "key": "chinese", "endonym": "中文", "tag": "zh-Hans", "dir": "ltr",
        "name_en": "Chinese",
        "title": "纽约市的免费帮助",
        "body": "本页列出了提供食物、医疗、住房帮助、法律帮助和经济援助的机构。"
                "几乎全部免费。大多数机构不会询问您的移民身份。",
        "sos": "如果有危险，请拨打 911。任何时间想找人倾诉，请拨打 988。两者都免费。",
        "interp": "下面的列表是英文的。请拨打 311 并要求中文口译员，"
                  "可以说明您需要普通话还是广东话。这项服务免费，任何时间都可以使用。",
        "search": "您也可以在搜索框中用中文输入。例如：食物、医生、住房。",
        "browse": "您需要什么帮助？",
        "cta": "查看提供中文服务的机构",
        "needs": {
            "safety": "我在家里不安全",
            "crisis": "我正在危机中，或者我需要有人倾诉",
            "food": "我需要食物",
            "housing": "我需要住的地方，或者我可能失去住房",
            "bills": "我收到医疗账单，或者保险公司拒赔",
            "doctor": "我需要看医生或牙医",
            "legal": "我需要律师，或者我有移民问题",
            "money": "我需要帮助支付费用",
            "family": "我需要孩子方面的帮助，或者我是独自一人的年轻人",
            "senior": "我是长者，或者我在照顾长者",
            "clothes": "我需要衣服、外套或婴儿用品",
            "work": "我需要工作或课程",
            "getting-there": "我需要交通方面的帮助",
            "veterans": "我曾在军队服役",
            "disability": "我有残疾，或者我在照顾残疾人",
            "record": "我有犯罪记录，或者我刚出狱",
            "start": "我不知道从哪里开始",
        },
    },
    {
        "key": "russian", "endonym": "Русский", "tag": "ru", "dir": "ltr",
        "name_en": "Russian",
        "title": "Бесплатная помощь в Нью-Йорке",
        "body": "На этой странице собраны места, где можно получить еду, "
                "медицинскую помощь, помощь с жильём, юридическую и денежную "
                "помощь. Почти всё бесплатно. Большинство из них не "
                "спрашивают об иммиграционном статусе.",
        "sos": "Если вам угрожает опасность, звоните 911. Чтобы поговорить с "
               "кем-то в любое время, звоните 988. Оба номера бесплатны.",
        "interp": "Список ниже составлен на английском языке. Позвоните по "
                  "номеру 311 и попросите переводчика на русский язык. Это "
                  "бесплатно и круглосуточно.",
        "search": "В строке поиска можно писать по-русски. Например: еда, врач, жильё.",
        "browse": "Что вам нужно?",
        "cta": "Показать места, где помогают на русском языке",
        "needs": {
            "safety": "Дома мне угрожает опасность",
            "crisis": "Я в кризисе, или мне нужно с кем-то поговорить",
            "food": "Мне нужна еда",
            "housing": "Мне негде жить, или я могу потерять жильё",
            "bills": "Мне пришёл счёт за лечение, или страховая отказала",
            "doctor": "Мне нужен врач или стоматолог",
            "legal": "Мне нужен юрист, или у меня вопрос об иммиграции",
            "money": "Мне нужна помощь с оплатой",
            "family": "Мне нужна помощь с детьми, или я молодой человек без поддержки",
            "senior": "Я пожилой человек, или я ухаживаю за пожилым",
            "clothes": "Мне нужна одежда, куртка или вещи для ребёнка",
            "work": "Мне нужна работа или курсы",
            "getting-there": "Мне нужна помощь с проездом",
            "veterans": "Я служил в армии",
            "disability": "У меня инвалидность, или я ухаживаю за человеком с инвалидностью",
            "record": "У меня судимость, или я вышел из заключения",
            "start": "Я не знаю, с чего начать",
        },
    },
    {
        "key": "bengali", "endonym": "বাংলা", "tag": "bn", "dir": "ltr",
        "name_en": "Bengali",
        "title": "নিউ ইয়র্ক সিটিতে বিনামূল্যে সাহায্য",
        "body": "এই পাতায় এমন জায়গার তালিকা আছে যেখানে খাবার, স্বাস্থ্যসেবা, "
                "বাসস্থানের সাহায্য, আইনি সাহায্য এবং আর্থিক সাহায্য পাওয়া যায়। "
                "প্রায় সবই বিনামূল্যে। বেশিরভাগ জায়গা আপনার অভিবাসন অবস্থা "
                "জিজ্ঞাসা করে না।",
        "sos": "বিপদে পড়লে 911 নম্বরে ফোন করুন। যেকোনো সময় কারও সঙ্গে কথা বলতে "
               "988 নম্বরে ফোন করুন। দুটোই বিনামূল্যে।",
        "interp": "নিচের তালিকাটি ইংরেজিতে লেখা। 311 নম্বরে ফোন করুন এবং বাংলা "
                  "দোভাষী চান। এটি বিনামূল্যে, যেকোনো সময়।",
        "search": "আপনি সার্চ বক্সে বাংলায়ও লিখতে পারেন। যেমন: খাবার, ডাক্তার, বাসস্থান।",
        "browse": "আপনার কী দরকার?",
        "cta": "বাংলায় সেবা দেয় এমন জায়গা দেখুন",
        "needs": {
            "safety": "আমি বাড়িতে নিরাপদ নই",
            "crisis": "আমি সংকটে আছি, বা আমার কারও সঙ্গে কথা বলা দরকার",
            "food": "আমার খাবার দরকার",
            "housing": "আমার থাকার জায়গা দরকার, বা আমি বাসা হারাতে পারি",
            "bills": "আমি চিকিৎসার বিল পেয়েছি, বা বীমা কোম্পানি না বলেছে",
            "doctor": "আমার ডাক্তার বা দাঁতের ডাক্তার দরকার",
            "legal": "আমার আইনজীবী দরকার, বা অভিবাসন নিয়ে প্রশ্ন আছে",
            "money": "খরচ মেটাতে আমার সাহায্য দরকার",
            "family": "আমার সন্তানের জন্য সাহায্য দরকার, বা আমি একা একজন তরুণ",
            "senior": "আমি একজন প্রবীণ, বা আমি একজনের যত্ন নিই",
            "clothes": "আমার জামাকাপড়, কোট বা শিশুর জিনিস দরকার",
            "work": "আমার কাজ বা ক্লাস দরকার",
            "getting-there": "যাতায়াতে আমার সাহায্য দরকার",
            "veterans": "আমি সেনাবাহিনীতে কাজ করেছি",
            "disability": "আমার প্রতিবন্ধকতা আছে, বা আমি এমন কারও যত্ন নিই",
            "record": "আমার অপরাধের রেকর্ড আছে, বা আমি জেল থেকে ফিরছি",
            "start": "আমি জানি না কোথা থেকে শুরু করব",
        },
    },
    {
        "key": "haitian-creole", "endonym": "Kreyòl Ayisyen", "tag": "ht", "dir": "ltr",
        "name_en": "Haitian Creole",
        "title": "Èd gratis nan vil New York",
        "body": "Paj sa a gen yon lis kote ki bay manje, swen sante, èd pou "
                "lojman, èd legal, ak èd lajan. Prèske tout bagay gratis. Pifò "
                "nan yo pa mande estati imigrasyon ou.",
        "sos": "Si ou an danje, rele 911. Pou pale ak yon moun nenpòt lè, rele "
               "988. Toude gratis.",
        "interp": "Lis ki anba a ekri an anglè. Rele 311 epi mande yon "
                  "entèprèt kreyòl ayisyen. Li gratis, nenpòt lè.",
        "search": "Ou ka ekri an kreyòl nan bwat rechèch la tou. Pa egzanp: manje, doktè, lojman.",
        "browse": "Ki sa ou bezwen?",
        "cta": "Gade kote ki sèvi moun ki pale kreyòl",
        "needs": {
            "safety": "Mwen pa an sekirite lakay mwen",
            "crisis": "Mwen nan kriz, oswa mwen bezwen pale ak yon moun",
            "food": "Mwen bezwen manje",
            "housing": "Mwen bezwen yon kote pou m rete, oswa mwen ka pèdi lojman m",
            "bills": "Mwen resevwa yon bòdwo medikal, oswa asirans mwen di non",
            "doctor": "Mwen bezwen wè yon doktè oswa yon dantis",
            "legal": "Mwen bezwen yon avoka, oswa mwen gen yon kesyon sou imigrasyon",
            "money": "Mwen bezwen èd pou peye bagay",
            "family": "Mwen bezwen èd ak pitit mwen, oswa mwen se yon jèn ki poukont li",
            "senior": "Mwen se yon granmoun, oswa m ap pran swen youn",
            "clothes": "Mwen bezwen rad, yon manto, oswa bagay pou tibebe",
            "work": "Mwen bezwen yon travay, oswa kou",
            "getting-there": "Mwen bezwen èd pou m rive",
            "veterans": "Mwen te sèvi nan lame",
            "disability": "Mwen gen yon andikap, oswa m ap pran swen yon moun ki gen youn",
            "record": "Mwen gen yon kazye jidisyè, oswa m ap soti nan prizon",
            "start": "Mwen pa konnen kote pou m kòmanse",
        },
    },
    {
        "key": "korean", "endonym": "한국어", "tag": "ko", "dir": "ltr",
        "name_en": "Korean",
        "title": "뉴욕시의 무료 지원",
        "body": "이 페이지에는 음식, 의료, 주거 지원, 법률 지원, 재정 지원을 "
                "제공하는 기관이 나와 있습니다. 거의 모두 무료입니다. 대부분의 "
                "기관은 이민 신분을 묻지 않습니다.",
        "sos": "위험한 상황이면 911로 전화하세요. 언제든 이야기하고 싶으면 "
               "988로 전화하세요. 둘 다 무료입니다.",
        "interp": "아래 목록은 영어로 되어 있습니다. 311로 전화해서 한국어 "
                  "통역사를 요청하세요. 무료이며 언제든지 이용할 수 있습니다.",
        "search": "검색창에 한국어로 입력해도 됩니다. 예: 음식, 의사, 주거.",
        "browse": "무엇이 필요하신가요?",
        "cta": "한국어로 도와주는 기관 보기",
        "needs": {
            "safety": "집에서 안전하지 않습니다",
            "crisis": "위기 상황이거나 이야기할 사람이 필요합니다",
            "food": "음식이 필요합니다",
            "housing": "머물 곳이 필요하거나 집을 잃을 수 있습니다",
            "bills": "의료비 청구서를 받았거나 보험이 거절했습니다",
            "doctor": "의사나 치과 의사가 필요합니다",
            "legal": "변호사가 필요하거나 이민 관련 질문이 있습니다",
            "money": "비용을 내는 데 도움이 필요합니다",
            "family": "아이 문제로 도움이 필요하거나 혼자인 청소년입니다",
            "senior": "저는 어르신이거나 어르신을 돌봅니다",
            "clothes": "옷, 외투 또는 아기 용품이 필요합니다",
            "work": "일자리나 수업이 필요합니다",
            "getting-there": "이동에 도움이 필요합니다",
            "veterans": "군에서 복무했습니다",
            "disability": "저는 장애가 있거나 장애가 있는 사람을 돌봅니다",
            "record": "전과가 있거나 출소했습니다",
            "start": "어디서 시작해야 할지 모르겠습니다",
        },
    },
    {
        "key": "arabic", "endonym": "العربية", "tag": "ar", "dir": "rtl",
        "name_en": "Arabic",
        "title": "مساعدة مجانية في مدينة نيويورك",
        "body": "تضم هذه الصفحة قائمة بأماكن تقدم الطعام والرعاية الصحية "
                "والمساعدة في السكن والمساعدة القانونية والمساعدة المالية. "
                "جميعها تقريبًا مجانية. ومعظمها لا يسأل عن وضعك من ناحية الهجرة.",
        "sos": "إذا كنت في خطر، اتصل بالرقم 911. وللتحدث مع شخص في أي وقت، "
               "اتصل بالرقم 988. كلاهما مجاني.",
        "interp": "القائمة أدناه مكتوبة بالإنجليزية. اتصل بالرقم 311 واطلب "
                  "مترجمًا للغة العربية. هذه الخدمة مجانية ومتاحة في أي وقت.",
        "search": "يمكنك أيضًا الكتابة بالعربية في مربع البحث. مثلاً: طعام، طبيب، سكن.",
        "browse": "ما الذي تحتاج إليه؟",
        "cta": "عرض الأماكن التي تقدم خدمات بالعربية",
        "needs": {
            "safety": "لست بأمان في المكان الذي أسكن فيه",
            "crisis": "أمر بأزمة، أو أحتاج إلى من أتحدث إليه",
            "food": "أحتاج إلى طعام",
            "housing": "أحتاج إلى مكان أقيم فيه، أو قد أفقد سكني",
            "bills": "وصلتني فاتورة طبية، أو رفض التأمين الدفع",
            "doctor": "أحتاج إلى طبيب أو طبيب أسنان",
            "legal": "أحتاج إلى محامٍ، أو لدي سؤال عن الهجرة",
            "money": "أحتاج إلى مساعدة في دفع التكاليف",
            "family": "أحتاج إلى مساعدة بشأن أطفالي، أو أنا شاب بمفردي",
            "senior": "أنا مسن، أو أرعى شخصًا مسنًا",
            "clothes": "أحتاج إلى ملابس أو معطف أو مستلزمات أطفال",
            "work": "أحتاج إلى عمل أو دورات دراسية",
            "getting-there": "أحتاج إلى مساعدة في التنقل",
            "veterans": "خدمت في الجيش",
            "disability": "لدي إعاقة، أو أرعى شخصًا لديه إعاقة",
            "record": "لدي سجل جنائي، أو خرجت من السجن",
            "start": "لا أعرف من أين أبدأ",
        },
    },
    {
        "key": "urdu", "endonym": "اردو", "tag": "ur", "dir": "rtl",
        "name_en": "Urdu",
        "title": "نیویارک شہر میں مفت مدد",
        "body": "اس صفحے پر ان جگہوں کی فہرست ہے جو کھانا، طبی علاج، رہائش میں "
                "مدد، قانونی مدد اور مالی مدد فراہم کرتی ہیں۔ تقریباً سب کچھ مفت "
                "ہے۔ زیادہ تر جگہیں آپ کی امیگریشن حیثیت نہیں پوچھتیں۔",
        "sos": "خطرے کی صورت میں 911 پر فون کریں۔ کسی سے بات کرنے کے لیے کسی بھی "
               "وقت 988 پر فون کریں۔ دونوں مفت ہیں۔",
        "interp": "نیچے دی گئی فہرست انگریزی میں ہے۔ 311 پر فون کریں اور اردو "
                  "مترجم مانگیں۔ یہ مفت ہے اور ہر وقت دستیاب ہے۔",
        "search": "آپ سرچ باکس میں اردو میں بھی لکھ سکتے ہیں۔ مثلاً: کھانا، ڈاکٹر، رہائش۔",
        "browse": "آپ کو کس چیز کی ضرورت ہے؟",
        "cta": "وہ جگہیں دیکھیں جو اردو میں مدد کرتی ہیں",
        "needs": {
            "safety": "میں اپنے گھر میں محفوظ نہیں ہوں",
            "crisis": "میں بحران میں ہوں، یا مجھے کسی سے بات کرنی ہے",
            "food": "مجھے کھانے کی ضرورت ہے",
            "housing": "مجھے رہنے کی جگہ چاہیے، یا میرا گھر چھن سکتا ہے",
            "bills": "مجھے طبی بل ملا ہے، یا انشورنس نے انکار کر دیا",
            "doctor": "مجھے ڈاکٹر یا دانتوں کے ڈاکٹر کی ضرورت ہے",
            "legal": "مجھے وکیل چاہیے، یا امیگریشن کا سوال ہے",
            "money": "مجھے اخراجات ادا کرنے میں مدد چاہیے",
            "family": "مجھے بچوں کے لیے مدد چاہیے، یا میں اکیلا نوجوان ہوں",
            "senior": "میں معمر ہوں، یا میں کسی معمر کی دیکھ بھال کرتا ہوں",
            "clothes": "مجھے کپڑے، کوٹ یا بچوں کا سامان چاہیے",
            "work": "مجھے کام یا کلاسیں چاہئیں",
            "getting-there": "مجھے آنے جانے میں مدد چاہیے",
            "veterans": "میں نے فوج میں خدمات انجام دی ہیں",
            "disability": "مجھے معذوری ہے، یا میں کسی معذور شخص کی دیکھ بھال کرتا ہوں",
            "record": "میرا مجرمانہ ریکارڈ ہے، یا میں جیل سے واپس آ رہا ہوں",
            "start": "مجھے معلوم نہیں کہاں سے شروع کروں",
        },
    },
    {
        "key": "french", "endonym": "Français", "tag": "fr", "dir": "ltr",
        "name_en": "French",
        "title": "Aide gratuite à New York",
        "body": "Cette page contient une liste de lieux qui offrent de la "
                "nourriture, des soins médicaux, une aide au logement, une aide "
                "juridique et une aide financière. Presque tout est gratuit. La "
                "plupart de ces lieux ne demandent pas votre statut d'immigration.",
        "sos": "En cas de danger, appelez le 911. Pour parler à quelqu'un à "
               "toute heure, appelez le 988. Les deux sont gratuits.",
        "interp": "La liste ci-dessous est en anglais. Appelez le 311 et "
                  "demandez un interprète en français. C'est gratuit, à toute heure.",
        "search": "Vous pouvez aussi écrire en français dans la barre de recherche. Par exemple : nourriture, avocat, logement.",
        "browse": "De quoi avez-vous besoin ?",
        "cta": "Voir les lieux qui aident en français",
        "needs": {
            "safety": "Je ne suis pas en sécurité chez moi",
            "crisis": "Je suis en crise, ou j'ai besoin de parler à quelqu'un",
            "food": "J'ai besoin de nourriture",
            "housing": "J'ai besoin d'un logement, ou je risque de perdre le mien",
            "bills": "J'ai reçu une facture médicale, ou mon assurance a refusé",
            "doctor": "J'ai besoin d'un médecin ou d'un dentiste",
            "legal": "J'ai besoin d'un avocat, ou j'ai une question d'immigration",
            "money": "J'ai besoin d'aide pour payer",
            "family": "J'ai besoin d'aide avec mes enfants, ou je suis un jeune seul",
            "senior": "Je suis une personne âgée, ou je m'occupe de quelqu'un",
            "clothes": "J'ai besoin de vêtements, d'un manteau ou d'articles pour bébé",
            "work": "J'ai besoin d'un emploi ou de cours",
            "getting-there": "J'ai besoin d'aide pour me déplacer",
            "veterans": "J'ai servi dans l'armée",
            "disability": "J'ai un handicap, ou je m'occupe de quelqu'un qui en a un",
            "record": "J'ai un casier judiciaire, ou je sors de prison",
            "start": "Je ne sais pas par où commencer",
        },
    },
    {
        "key": "polish", "endonym": "Polski", "tag": "pl", "dir": "ltr",
        "name_en": "Polish",
        "title": "Bezpłatna pomoc w Nowym Jorku",
        "body": "Na tej stronie znajduje się lista miejsc, które oferują "
                "jedzenie, opiekę zdrowotną, pomoc mieszkaniową, pomoc prawną i "
                "pomoc finansową. Prawie wszystko jest bezpłatne. Większość tych "
                "miejsc nie pyta o status imigracyjny.",
        "sos": "W razie niebezpieczeństwa zadzwoń pod numer 911. Aby z kimś "
               "porozmawiać o każdej porze, zadzwoń pod numer 988. Oba są bezpłatne.",
        "interp": "Lista poniżej jest po angielsku. Zadzwoń pod numer 311 i "
                  "poproś o tłumacza języka polskiego. To bezpłatne, o każdej porze.",
        "search": "W wyszukiwarce możesz pisać po polsku. Na przykład: jedzenie, prawnik, mieszkanie.",
        "browse": "Czego potrzebujesz?",
        "cta": "Zobacz miejsca, które pomagają po polsku",
        "needs": {
            "safety": "Nie jestem bezpieczny w swoim domu",
            "crisis": "Jestem w kryzysie albo potrzebuję z kimś porozmawiać",
            "food": "Potrzebuję jedzenia",
            "housing": "Potrzebuję miejsca do spania albo mogę stracić mieszkanie",
            "bills": "Dostałem rachunek za leczenie albo ubezpieczyciel odmówił",
            "doctor": "Potrzebuję lekarza albo dentysty",
            "legal": "Potrzebuję prawnika albo mam pytanie o imigrację",
            "money": "Potrzebuję pomocy w opłaceniu rachunków",
            "family": "Potrzebuję pomocy z dziećmi albo jestem młodą osobą bez wsparcia",
            "senior": "Jestem osobą starszą albo opiekuję się taką osobą",
            "clothes": "Potrzebuję ubrań, kurtki albo rzeczy dla dziecka",
            "work": "Potrzebuję pracy albo kursów",
            "getting-there": "Potrzebuję pomocy z dojazdem",
            "veterans": "Służyłem w wojsku",
            "disability": "Mam niepełnosprawność albo opiekuję się osobą z niepełnosprawnością",
            "record": "Mam wyrok albo wracam z więzienia",
            "start": "Nie wiem, od czego zacząć",
        },
    },
]

# Every language must name every need, or somebody who cannot read English
# reaches a heading that is not there. Checked at build time, not by eye.
for _L in LANGUAGES:
    for _f in ("title", "body", "sos", "interp", "browse", "cta", "search"):
        if not _L.get(_f):
            raise SystemExit(f'{_L["name_en"]} panel has no {_f!r}')
    _missing = [n["key"] for n in NEEDS if n["key"] not in _L["needs"]]
    if _missing:
        raise SystemExit(f'{_L["name_en"]} has no label for: {_missing}')
    _extra = [k for k in _L["needs"] if k not in {n["key"] for n in NEEDS}]
    if _extra:
        raise SystemExit(f'{_L["name_en"]} labels a need that does not exist: {_extra}')

LANG_MATCH = {
    "spanish": ["spanish", "español", "espanol"],
    "chinese": ["chinese", "mandarin", "cantonese"],
    "russian": ["russian"],
    "bengali": ["bengali", "bangla"],
    "haitian-creole": ["haitian", "creole", "kreyol"],
    "korean": ["korean"],
    "arabic": ["arabic"],
    "urdu": ["urdu"],
    "french": ["french", "francais", "français"],
    "polish": ["polish", "polski"],
}


# ------------------------------------------------------- words people use
# The directory is written in the vocabulary of the agencies that run these
# programmes. Nobody searches for "SNAP", "paratransit" or "ESOL"; they search
# for "food stamps", "access-a-ride" and "english classes". Left alone, a
# search for "food stamps" returned one row out of fourteen food programmes,
# and "dentist" returned one of two dental clinics.
#
# So each row's hidden search text is expanded at build time: if the row
# already contains a trigger on the left, the words on the right are appended
# to what it matches. Expanding documents rather than queries keeps the
# runtime a plain substring test, and keeps the whole table in one reviewable
# place. These are the words, not synonyms in the abstract — "kicked out" is
# in here because that is what somebody facing eviction types.
SYNONYMS = [
    ("snap",            "food stamps ebt"),
    ("pantry",          "free food groceries hungry"),
    ("soup kitchen",    "free meal hot meal hungry"),
    ("dental",          "dentist teeth tooth toothache"),
    ("fqhc",            "clinic doctor checkup primary care"),
    ("medication",      "medicine pills prescription pharmacy drug costs"),
    ("health insurance","obamacare aca marketplace coverage medicaid"),
    ("medicare",        "medicare part b senior insurance"),
    ("eviction",        "evicted landlord kicked out lose my apartment"),
    ("tenant",          "landlord rent apartment lease"),
    ("shelter",         "homeless nowhere to sleep sleep tonight bed"),
    ("housing",         "rent apartment place to live"),
    ("affordable housing", "section 8 voucher vouchers housing voucher cityfheps "
                        "nycha public housing lottery"),
    ("utility",         "con ed electric bill gas bill heat heating pay paying cant pay "
                        "shut off my power power shut off no electricity no heat "
                        "no hot water lights turned off disconnected"),
    ("income support",  "welfare public assistance cash benefits pay paying rent money"),
    ("immigration",     "green card papers undocumented ice deportation asylum visa "
                        "raid detained knocked on my door came to my work"),
    ("know your rights","ice at my door immigration agents raid detained arrested "
                        "do i have to open the door what do i say"),
    ("legal",           "lawyer attorney court sue rights"),
    ("domestic violence","abuse abusive hits me hitting me beat me beats me hurt me "
                        "hurting me scared afraid threatens threatening husband wife "
                        "boyfriend girlfriend partner unsafe at home violent assault "
                        "choked stalking restraining order"),
    ("dv ",             "hits me scared afraid husband boyfriend partner abuse"),
    ("survivor",        "abuse assault rape raped attacked scared afraid "
                        "daughter son sister mother wife husband child"),
    # The four highest-stakes searches on this page returned NOTHING before
    # these lines existed: "my husband hits me", "im scared of my boyfriend",
    # "i want to die", "heroin". Somebody types what is happening to them, in
    # their own words, and the directory answered with a blank page. Nobody
    # in that state types "domestic violence" or "substance use disorder" —
    # those are the words the agencies use about them afterwards.
    ("crisis",          "suicide suicidal want to die kill myself killing myself "
                        "end my life hopeless cant go on talk to someone "
                        "someone to talk to lonely panic breakdown emergency help now"),
    ("substance",       "drugs alcohol addiction overdose drinking recovery heroin "
                        "fentanyl opioid opioids cocaine crack meth pills detox "
                        "relapse rehab sober high using"),
    ("overdose",        "narcan naloxone overdosing heroin fentanyl opioid"),
    ("addiction",       "heroin fentanyl opioid cocaine meth pills detox rehab drinking"),
    ("mental health",   "depressed depression anxiety therapy counseling"),
    ("senior",          "elderly older adult grandmother grandfather"),
    ("paratransit",     "access-a-ride access a ride wheelchair disabled ride"),
    ("rides",           "ride to the doctor ride to appointment transportation "
                        "get to my appointment"),
    ("transit",         "fair fares metrocard subway bus fare"),
    ("early childhood", "daycare day care pre-k prek 3-k 3k kindergarten childcare "
                        "babysitting head start preschool nursery"),
    ("youth",           "teen teenager kid young person"),
    ("job",             "work employment hiring career resume training classes"),
    ("esol",            "english classes esl learn english"),
    ("veteran",         "army navy marines air force service member"),
    ("hiv",             "aids positive status testing hiv test std sti"),
    ("reproductive",    "abortion terminate a pregnancy pregnancy options "
                        "birth control pregnancy test prenatal"),
    ("abortion",        "abortion pregnancy options terminate"),
    ("diaper",          "baby supplies formula newborn"),
    ("coat",            "winter clothes jacket warm"),
    ("clothing",        "clothes shoes free clothes"),
    ("tax",             "taxes refund filing irs w2"),
    ("identification",  "id card birth certificate documents"),
    ("citywide info",   "not sure where to start dont know where to start where to begin "
                        "anything else who do i call interpreter translation "
                        "in my language somebody who speaks my language"),
    ("benefits eligibility", "what can i get what am i eligible for do i qualify "
                        "benefits screener see what i qualify for"),
    ("social services search", "not sure where to start find services near me"),

    # Added after a second sweep of real phrasings against the rebuilt search.
    # Each one is a query that returned nothing, or returned the wrong thing
    # confidently, until the trigger on the left carried the words on the right.
    ("medical bills",   "hospital bill cant pay my hospital bill bills i cant pay "
                        "surprise bill collections owe the hospital"),
    ("hospital bill",   "charity care financial assistance bill i cannot pay "
                        "cant pay hospital wrote off forgiven"),
    ("denied claims",   "denied claim insurance said no denial appeal "
                        "they wont cover it refused to pay"),
    ("insurance denial","appeal external review denied coverage they said no "
                        "claim denied my claim rejected"),
    ("medical debt",    "debt collector collections credit report owe money hospital"),
    ("copay",           "medicine too expensive cant afford my medicine prescription cost"),
    ("prescription",    "medicine too expensive cant afford my pills pharmacy cost"),
    ("repairs",         "landlord wont fix no heat no hot water mold leak broken"),
    ("tenant rights",   "landlord wont fix no heat no hot water repairs harassment lockout"),
    ("arrears",         "back rent behind on rent owe rent rent money"),
    ("emergency cash",  "back rent behind on rent one shot deal cant pay rent"),
    ("free civil legal","benefits cut off my benefits were cut off they cut off my "
                        "benefits stopped my benefits stopped my food stamps denied "
                        "benefits fair hearing"),
    ("benefits",        "cut off stopped denied fair hearing appeal my case"),
    ("workers",         "wages unpaid wages not paid me wage theft boss stole my pay "
                        "overtime fired didnt pay me they didnt pay me"),
    ("rights at work",  "unpaid wages wage theft not paid boss stole my pay overtime "
                        "minimum wage fired retaliation sick leave"),
    ("discrimination",  "refused to rent to me wouldnt hire me because of my record "
                        "because im disabled because im pregnant landlord refused voucher"),
    ("employment",      "wages unpaid wages wage theft fired discrimination at work"),
    ("clinic",          "free clinic no insurance uninsured cant afford a doctor "
                        "sliding scale"),
    ("health access",   "no insurance uninsured undocumented no papers see a doctor "
                        "free clinic cheap clinic cant afford a doctor"),
    ("criminal record", "background check turned down for a job sealing my record "
                        "expunge felony conviction came home from prison parole probation"),
    ("reentry",         "came home from prison out of jail parole probation "
                        "background check record"),
    ("disability",      "disabled ssi ssdi wheelchair blind deaf accommodation "
                        "cant work because"),
    ("trafficking",     "forced to work took my passport wont let me leave "
                        "controlling my money"),
    ("victim",          "crime victim compensation reimburse funeral robbed attacked"),
    ("cancer",          "chemo chemotherapy oncology treatment tumor"),
    ("after a fire",    "fire burned my apartment burned down lost everything flood "
                        "flooded disaster displaced red cross"),
    ("after a death",   "funeral burial cremation died passed away cant afford a funeral"),
    ("after a shooting","shot shooting gun violence killed murdered lost my son "
                        "my son was shot my daughter was shot"),
    ("lodging",         "place to stay during treatment far from the hospital"),
]


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def esc(s):
    return html.escape(s or "", quote=True)


def contact(phone):
    """(kind, label, href) for the one action button on a row.

    Three shapes appear in the data and they are not interchangeable:

      "917-720-9700"                    -> call it
      "800-621-4673 (800-621-HOPE)"     -> call the first, drop the mnemonic
      "988 then press 1 / text 838255"  -> call 988. Naively stripping
          non-digits across the whole cell yields +19881838255, which is a
          number that does not exist; this is the bug that makes a crisis line
          unreachable, so the cell is cut at the first separator FIRST and
          only then reduced to digits.
      "Text HOME to 741741"             -> a text shortcode. It cannot be
          dialled at all, so it must not render as a Call button.

    Anything with no reachable number returns ("none", "", ""), and the row
    falls back to its website.
    """
    if not phone:
        return ("none", "", "")

    # A text-only line: no dialable number, an sms: target instead.
    m = re.match(r"\s*text\s+(\S+)\s+to\s+([0-9\-]+)", phone, flags=re.I)
    if m:
        return ("text", phone.split(";")[0].strip(), "sms:" + re.sub(r"[^0-9]", "", m.group(2)))

    # Cut to the first alternative before touching the digits.
    first = re.split(r"[;/(]|\bthen\b|\bor\b", phone, flags=re.I)[0]
    digits = re.sub(r"[^0-9]", "", first)
    if not digits:
        return ("none", "", "")

    label = re.sub(r"\s*\(.*?\)", "", first).strip().rstrip(",")
    if len(digits) <= 4:            # 311, 911, 988
        href = digits
    elif len(digits) == 10:
        href = "+1" + digits
    elif len(digits) == 11 and digits.startswith("1"):
        href = "+" + digits
    else:
        return ("none", "", "")     # malformed rather than guess at a number
    return ("call", label, href)


# A cross-reference keyword matches at a WORD START, never anywhere in the
# string. Plain substring matching put a soup kitchen, a diaper bank and a
# hospital-bill charity on the disability page, because "ssi" is inside
# a-ssi-stance, mi-ssi-on and a-ssi-stors. It is the same bug the search box
# had with "ice" inside serv-ice, off-ice and just-ice, and it is worse here:
# the search is something somebody typed and can retype, and this decides
# what a page IS.
_ALSO_RE = {}


def _fires(kw, hay):
    r = _ALSO_RE.get(kw)
    if r is None:
        r = _ALSO_RE[kw] = re.compile(r"\b" + re.escape(kw))
    return bool(r.search(hay))


def needs_for(row):
    """Every sentence this resource answers.

    Its own category always counts. `also` keywords add the needs it answers
    from somewhere else — a health-insurance helpline is both "seeing a
    doctor" and "this bill" — matched against what the row IS (its name and
    subcategory) and never against its description, because nearly every
    description mentions cost and immigration status.
    """
    found = []
    cat = row["Category"]
    hay = ((row["Subcategory"] or "") + " " + (row["Resource Name"] or "")).lower()
    for need in NEEDS:
        if cat in need.get("cats", []):
            found.append(need["key"])
            continue
        if any(_fires(kw, hay) for kw in need.get("also", [])):
            found.append(need["key"])
    return found or ["start"]


def boroughs_for(row):
    """Borough tokens. Citywide and national resources match every borough.

    Getting this wrong in the generous direction shows somebody a resource
    that turns out to be in another borough. Getting it wrong in the strict
    direction hides a citywide hotline from them entirely, so when the cell is
    ambiguous, match everything.
    """
    cell = (row["Boroughs Served"] or "").lower()
    if "citywide" in cell or "national" in cell or "statewide" in cell:
        return [k for k, _ in BOROUGHS] + ["citywide"]
    hits = [k for k, label in BOROUGHS if label.lower() in cell]
    if "bronx" in cell and "bronx" not in hits:
        hits.append("bronx")
    return hits or [k for k, _ in BOROUGHS] + ["citywide"]


# "Multiple" is what 77 of the 118 rows say under Languages, and on its own it
# matched no chip at all — so filtering by Español hid two thirds of the
# directory, and filtering by العربية, which no row names explicitly, left six
# places out of a hundred and eighteen. A filter that hides help is worse than
# no filter.
#
# So a vague-but-real answer counts as "many": it is not a promise that they
# speak Arabic, it is what the directory actually knows, which is that they
# work in more than one language and usually through an interpreter. The chip
# matches a named language OR "many", and the filter says so in plain words
# rather than implying a guarantee it cannot make.
VAGUE_LANG = re.compile(
    r"multiple|\d+\+? ?languages|interpret|all languages|language line", re.I)


def langs_for(row):
    cell = (row["Languages"] or "").lower()
    hits = [key for key, words in LANG_MATCH.items() if any(w in cell for w in words)]
    if VAGUE_LANG.search(cell):
        hits.append("many")
    return hits


def flags_for(row):
    """The four facts that decide whether somebody dares to call."""
    f = []
    cost = (row["Cost"] or "").lower()
    hours = (row["Hours"] or "").lower()
    tags = (row["Tags"] or "").lower()
    access = (row["Access Type"] or "").lower()
    if cost.startswith("free"):
        f.append("free")
    if "24/7" in hours or "24-7" in tags or "24 hours" in hours:
        f.append("open-247")
    if row["Undocumented-Friendly"].strip().lower() == "yes":
        f.append("no-status")
    if "walk-in" in hours or "walk in" in (row["Notes"] or "").lower():
        f.append("walk-in")
    for token, key in [("phone", "phone"), ("online", "online"),
                       ("in-person", "in-person"), ("text", "text"), ("chat", "chat")]:
        if token in access:
            f.append(key)
    return f


# The emergency strip, curated by hand and not by rule.
#
# A heuristic over tags and hours got this wrong in exactly the way that
# matters: it put a hospital switchboard and two copies of 988 in front of
# somebody in danger. Four lines, each answering a different emergency, each
# free, each answered by a person at any hour. The wording beside each number
# is written for the person reading it, not lifted from the directory's
# internal subcategory. Changing this list is a safety decision.
SOS = [
    ("NYC 988 (formerly NYC Well)",
     "You feel unsafe with yourself, or you need to talk to somebody now"),
    ("NYC HOPE — 24-Hour DV Hotline (Safe Horizon)",
     "Someone at home or a partner is hurting you or frightening you"),
    ("NYC 311",
     "Anything else at all. Free, any hour, in your language"),
]


def urgent(row):
    """True for the hand-picked emergency lines above."""
    return row["Resource Name"] in [name for name, _ in SOS]


MONTHS = ("January February March April May June July August September "
          "October November December").split()


def checked(rows):
    """"Checked August 2026", derived from the data rather than typed.

    It was typed, in three places, and by the time anybody looked two of them
    said June and one said August — on the sheets students hand to people, as
    the answer to "how do I know this is still right".
    """
    dates = sorted(r["Last Verified"] for r in rows if r.get("Last Verified"))
    if not dates:
        return "not yet checked"
    y, m, _ = dates[-1].split("-")
    return f"{MONTHS[int(m) - 1]} {y}"


def load():
    with open(CSV, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    out = []
    for row in rows:
        row = {k: (v or "").strip() for k, v in row.items()}
        if not row.get("Resource Name"):
            continue
        for _f in ("Resource Name", "Subcategory", "Description", "Who Can Access",
                   "Notes", "Cost", "Hours", "Languages", "Address / Location"):
            row[_f] = prose(row.get(_f, ""))
        row["_needs"] = needs_for(row)
        row["_boroughs"] = boroughs_for(row)
        row["_langs"] = langs_for(row)
        row["_flags"] = flags_for(row)
        row["_urgent"] = urgent(row)
        row["_id"] = slug(row["Resource Name"])
        out.append(row)
    return out


def tagtext(r):
    """What we filed this row as: its tags and its category.

    Separate from the synonym expansion below, and weighted above it, because
    a row we deliberately tagged "wheelchair" is a better answer to the query
    "wheelchair" than one that inherited the word from being tagged
    "disability". Explicit beats attached.
    """
    return " ".join([r["Tags"].replace(";", " "), r["Category"]]).lower()


def haystack(r):
    """The plain-English words somebody would actually type for this row.

    Only vocabulary that is NOT already visible in the row and NOT in its
    tags: every phrase SYNONYMS attaches. help.js scores this below the row's
    own text, because it is deliberately generous — every row tagged
    "disability" carries "blind", "deaf" and "wheelchair" so that those
    searches find something, and weighted equally a meal-delivery service
    outranked Lighthouse Guild on "im blind".
    """
    # What a synonym is allowed to fire on: the fields that say what this
    # resource IS. Description and Notes are deliberately excluded — most rows
    # carry a note like "does not ask about immigration status", and letting
    # that fire the immigration trigger attached "green card" to 29 unrelated
    # rows, so a search for "green card" returned a food pantry and a DV
    # hotline before it reached a single immigration lawyer.
    base = " ".join([
        r["Resource Name"], r["Subcategory"], r["Tags"], r["Category"],
    ]).lower()
    extra = []
    for trigger, words in SYNONYMS:
        if trigger in base:
            extra.append(words)
    return " ".join(extra).lower()


def needwords(keys):
    """The ten-language query vocabulary for a set of needs, as one string.

    Shipped once per page and once in the search index, never once per row.
    Attached to every row it applies to, it added 160 KB to the front page —
    the same eighteen words repeated three hundred times — for something that
    is identical across every row sharing a need.
    """
    out = []
    for key in keys:
        out.extend(NEED_WORDS.get(key, []))
    return " ".join(out).lower()


# --------------------------------------------------------------- rendering
# Every icon is one path on a 24-box, drawn in currentColor. Inline because a
# sprite sheet is one more request on the page most likely to be opened on a
# bad connection, and because these need to survive the page being printed.
ICONS = {
    "shield": "M12 3 4 6v6c0 5 3.4 8.4 8 9 4.6-.6 8-4 8-9V6l-8-3Z",
    "heart": "M12 20s-7-4.5-7-9.5A4 4 0 0 1 12 8a4 4 0 0 1 7 2.5C19 15.5 12 20 12 20Z",
    "bowl": "M4 11h16a8 8 0 0 1-16 0ZM9 7c0-1 1-1.5 1-2.5M13 7c0-1 1-1.5 1-2.5M3 20h18",
    "roof": "M3 11 12 4l9 7M6 10v9h12v-9M10 19v-5h4v5",
    "bill": "M6 3h12v18l-3-2-3 2-3-2-3 2V3ZM9 8h6M9 12h6M9 16h3",
    "cross": "M10 3h4v7h7v4h-7v7h-4v-7H3v-4h7V3Z",
    "scale": "M12 4v16M6 20h12M12 6 5 10h8L6 10M12 6l7 4h-8l7 0M3 10a3 3 0 0 0 6 0M15 10a3 3 0 0 0 6 0",
    "wallet": "M3 7h15a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7Zm0 0 12-3v3M16 13h2",
    "family": "M8 8a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5Zm8 1a2 2 0 1 0 0-4 2 2 0 0 0 0 4ZM4 20v-4a4 4 0 0 1 8 0v4M14 20v-3a3 3 0 0 1 6 0v3",
    "senior": "M12 7a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5Zm-2 3h4l1 5-2 1v6M10 10 8 15l2 1v6M17 12v10",
    "coat": "M12 3 7 5v16h10V5l-5-2Zm0 0v18M7 9l-3 2v7M17 9l3 2v7",
    "work": "M3 8h18v12H3V8Zm6 0V5h6v3M3 13h18",
    "bus": "M5 4h14v11H5V4Zm0 11 1 4h2l1-4m6 0 1 4h2l1-4M5 9h14M8 12h.01M16 12h.01",
    "star": "m12 3 2.6 5.6 6 .8-4.4 4.2 1.1 6.1L12 16.8 6.7 19.7l1.1-6.1L3.4 9.4l6-.8L12 3Z",
    "compass": "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Zm3.5-12.5-2 5-5 2 2-5 5-2Z",
    "gate": "M4 21V6a2 2 0 0 1 2-2h6v17M4 21h16M20 21V10l-8-4M8 12h.01M15 13h.01",
    # The international access symbol, drawn as one stroke rather than the
    # filled glyph, so it sits with the other fifteen instead of shouting.
    "access": "M12 5.5a1.6 1.6 0 1 0 0-3.2 1.6 1.6 0 0 0 0 3.2ZM9 8.2l3 .9 3-.6M12 9v4h4l2.5 6M12 13a4.6 4.6 0 1 0 3.6 7.4",
}


def icon(name):
    d = ICONS.get(name, ICONS["compass"])
    return (f'<svg class="ico" viewBox="0 0 24 24" aria-hidden="true" '
            f'fill="none" stroke="currentColor" stroke-width="1.6" '
            f'stroke-linecap="round" stroke-linejoin="round"><path d="{d}"/></svg>')


# The four badges worth putting on the row itself. Everything else lives one
# tap down in the details, because a row that says eight things says nothing.
BADGES = [
    ("free", "Free"),
    ("open-247", "Open 24/7"),
    ("no-status", "No immigration status asked"),
]


def render_row(r, need_key):
    """One resource. The two things somebody needs are the name and the number,
    so those are the two things that are big; the rest is one tap down.

    A resource filed under two needs is rendered twice, so the id has to carry
    the group: duplicate ids would break every anchor on the page and make a
    screen reader announce two different rows by the same name. `data-key` is
    the shared identity, which is how the counter below says "43 places" and
    not "45" when both copies of two resources are showing.
    """
    a = []
    a.append(f'<li class="r" id="r-{esc(need_key)}-{esc(r["_id"])}"'
             f' data-key="{esc(r["_id"])}"'
             f' data-needs="{esc(" ".join(r["_needs"]))}"'
             f' data-boro="{esc(" ".join(r["_boroughs"]))}"'
             f' data-lang="{esc(" ".join(r["_langs"]))}"'
             f' data-flags="{esc(" ".join(r["_flags"]))}"'
             f' data-tags="{esc(tagtext(r))}"'
             f' data-find="{esc(haystack(r))}">')
    a.append('<div class="r__head">')
    a.append(f'<h3 class="r__name">{esc(r["Resource Name"])}</h3>')
    if r["Subcategory"]:
        a.append(f'<p class="r__kind">{esc(r["Subcategory"])}</p>')
    a.append("</div>")
    a.append(f'<p class="r__what">{esc(r["Description"])}</p>')

    badges = [f'<span class="bdg bdg--{k}">{v}</span>'
              for k, v in BADGES if k in r["_flags"]]
    if badges:
        a.append('<p class="r__badges">' + "".join(badges) + "</p>")

    # actions
    a.append('<div class="r__do">')
    kind, label, href = contact(r["Phone"])
    if kind == "call":
        a.append(f'<a class="call" href="tel:{esc(href)}">'
                 f'<svg class="ico" aria-hidden="true"><use href="#i-phone"/></svg>'
                 f'<span><small>Call</small>{esc(label)}</span></a>')
    elif kind == "text":
        a.append(f'<a class="call call--text" href="{esc(href)}">'
                 f'<svg class="ico" aria-hidden="true"><use href="#i-text"/></svg>'
                 f'<span><small>Text</small>{esc(label)}</span></a>')
    if r["Website"]:
        a.append(f'<a class="visit" href="{esc(r["Website"])}" rel="noopener">'
                 f'<span class="visit__t">Open website</span>'
                 f'<span class="arr" aria-hidden="true">&#8599;</span></a>')
    a.append("</div>")

    # details
    facts = [
        ("Phone", r["Phone"]),
        ("Who it is for", r["Who Can Access"]),
        ("Cost", r["Cost"]),
        ("Hours", r["Hours"]),
        ("Languages", r["Languages"]),
        ("Where", r["Address / Location"]),
        ("Boroughs", r["Boroughs Served"]),
        ("How to reach them", r["Access Type"]),
    ]
    facts = [(k, v) for k, v in facts if v and v.lower() not in ("n/a", "-")]
    facts = [(k, "Multiple languages — ask when you call" if k == "Languages"
                 and v.strip().lower() == "multiple" else v) for k, v in facts]
    a.append('<details class="r__more"><summary><span>More about this</span></summary>'
             '<div class="r__facts"><dl>')
    for k, v in facts:
        a.append(f"<dt>{esc(k)}</dt><dd>{esc(v)}</dd>")
    a.append("</dl>")
    if r["Notes"]:
        a.append(f'<p class="r__note">{esc(r["Notes"])}</p>')
    if r["Last Verified"]:
        a.append(f'<p class="r__ver">We checked this on {esc(r["Last Verified"])}.</p>')
    a.append("</div></details>")
    a.append("</li>")
    return "\n".join(a)


HONESTY = (
    "We are trained student volunteers. We help you find the free programs and "
    "professionals in New York that handle medical bills and insurance denials. "
    "We are not doctors, lawyers, benefits counselors, or insurance experts. We "
    "do not read your bills, fill out your forms, or tell you what you qualify "
    "for. We connect you to people who do that, and they do it for free. We "
    "never charge for anything."
)


# ---------------------------------------------------- which group a row is in
def group_for(row, need_key):
    """The second-level bucket, matched against what the row says it is.

    Order matters: the first rule that fires wins, so the specific buckets are
    listed above the general ones in GROUPS. Never matches on Description or
    Notes — nearly every row's note mentions immigration status or cost, and
    letting prose fire these rules put food pantries under "Immigration".
    """
    # Subcategory and name only. Tags are search vocabulary, deliberately
    # generous — a community health centre is tagged "dental" so that somebody
    # searching for a dentist finds it — and letting that generosity decide
    # where a row FILES put sixteen general clinics under "Teeth". What a row
    # is called and what it calls itself are the two fields that say what it
    # is; the tags say what it can also answer.
    hay = " ".join([row["Subcategory"], row["Resource Name"]]).lower()
    buckets = GROUPS.get(need_key)
    if not buckets:
        return "more"
    for key, _label, words in buckets:
        # A bucket whose keywords are all boroughs is asking about the borough
        # field, not about the row's name. It is the one axis a neighbourhood
        # organisation is genuinely sorted by, and "One place that does
        # everything" was eighteen rows deep without it.
        if words and all(w in BORO_WORDS for w in words):
            where = " ".join(row["_boroughs"])
            if any(w in where for w in words):
                return key
            continue
        # Word starts, exactly as in needs_for. The same "ice" bug lived here
        # too and was invisible until the labels changed: `ice` matched
        # serv-*ice*-s and Just-*ice*, so "Immigrant services", "TakeRoot
        # Justice" and "Brooklyn Defender Services" all filed themselves under
        # Immigration.
        if any(_fires(w, hay) for w in words):
            return key
    return buckets[-1][0]


def need_by_key(key):
    for need in NEEDS:
        if need["key"] == key:
            return need
    raise KeyError(key)


def page_for(need_key):
    return f"help-{need_key}.html"


def ordered(rows, key):
    """Within a need, the resource somebody should try first leads.

    `start-here` is a tag in the data, applied to the row that is genuinely
    the best opening move for that need. Everything else keeps CSV order,
    which is hand-ordered per group.
    """
    group = [r for r in rows if key in r["_needs"]]
    return sorted(group, key=lambda r: 0 if "start-here" in r["Tags"] else 1)


# --------------------------------------------------------------- fragments
FONTS = ('<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,'
         'opsz,wght@0,9..144,400;0,9..144,500;1,9..144,400&family=Inter:wght@'
         '400;500;600;700&display=swap" rel="stylesheet" />')

SPRITE = ('<svg class="sprite" aria-hidden="true"><symbol id="i-phone" viewBox="0 0 24 24" '
          'fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
          'stroke-linejoin="round"><path d="M6 3h3l2 5-2.5 1.5a12 12 0 0 0 6 6L16 13l5 2v3a2 '
          '2 0 0 1-2.2 2A17 17 0 0 1 4 5.2 2 2 0 0 1 6 3Z"/></symbol>'
          '<symbol id="i-text" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
          'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
          '<path d="M21 12a8 8 0 0 1-8 8H4l2.2-2.6A8 8 0 1 1 21 12Z"/></symbol></svg>')

PIN = ('<svg viewBox="0 0 32 32" aria-hidden="true"><path class="pin" d="M16 2 C9 2 5 7 5 13 '
       'c0 7 8 15 11 17 3-2 11-10 11-17 0-6-4-11-11-11Z"/>'
       '<circle class="pin-dot" cx="16" cy="13" r="4.2"/></svg>')


def head(title, desc, skip_href, skip_label):
    return [
        '<!DOCTYPE html>', '<html lang="en">', '<head>',
        '<meta charset="UTF-8" />',
        '<meta name="viewport" content="width=device-width, initial-scale=1.0" />',
        f'<title>{esc(title)}</title>',
        f'<meta name="description" content="{esc(desc)}" />',
        '<meta name="theme-color" content="#13231A" />',
        f'<meta property="og:title" content="{esc(title)}" />',
        f'<meta property="og:description" content="{esc(desc)}" />',
        '<meta property="og:type" content="website" />',
        '<link rel="preconnect" href="https://fonts.googleapis.com" />',
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />',
        FONTS,
        '<link rel="stylesheet" href="tokens.css" />',
        '<link rel="stylesheet" href="help.css" />',
        '</head>',
        '<body class="help" id="top">',
        f'<a class="skip" href="{skip_href}">{esc(skip_label)}</a>',
        SPRITE,
    ]


def header_frag():
    return [
        '<header class="hhead">',
        '  <div class="hhead__in">',
        '    <a class="brand" href="index.html" aria-label="Waypoint home">',
        f'      {PIN}',
        '      <span class="brand__txt">Waypoint<small>Student Health Corps</small></span>',
        '    </a>',
        '    <nav class="hhead__links" aria-label="Primary">',
        '      <a href="help.html" aria-current="page">Find help</a>',
        '      <a href="index.html#students">Students</a>',
        '      <a href="index.html#partners">Partners</a>',
        '    </nav>',
        '  </div>',
        '</header>',
    ]


def langbar_frag():
    """Language access, first thing under the header, on every resident page.

    Somebody who cannot read the page should not have to read the page to find
    their way off it — and that is as true on "I need food" as it is on the
    front of the directory, so this ships on all of them rather than only on
    the one somebody happened to enter through.
    """
    out = ['<section class="langbar" aria-labelledby="langbar-h">',
           '  <h2 id="langbar-h" class="langbar__h">Get help in your language</h2>',
           '  <ul class="langbar__list">']
    for L in LANGUAGES:
        out.append(f'    <li><a href="#lang-{L["key"]}" lang="{L["tag"]}" '
                   f'data-lang="{L["key"]}"{" dir=rtl" if L["dir"] == "rtl" else ""}>'
                   f'{esc(L["endonym"])}</a></li>')
    out += ['  </ul>', '</section>']
    for L in LANGUAGES:
        rtl = ' dir="rtl"' if L["dir"] == "rtl" else ""
        out += [
            f'<section class="langnote" id="lang-{L["key"]}" lang="{L["tag"]}"{rtl} '
            f'data-lang="{L["key"]}" aria-labelledby="lang-h-{L["key"]}">',
            f'  <h2 id="lang-h-{L["key"]}">{esc(L["title"])}</h2>',
            f'  <p>{esc(L["body"])}</p>',
            f'  <p class="langnote__sos">{esc(L["sos"])}</p>',
            f'  <p class="langnote__interp">{esc(L["interp"])}</p>',
        ]
        # The sixteen kinds of help, named in this language, each opening its
        # own page. This is the difference between a notice that acknowledges
        # somebody exists and a page they can actually use: without it, a
        # reader who cannot read English is told in their language that the
        # list below is in English, and then left with it.
        out += [
            f'  <p class="langnote__search">{esc(L["search"])}</p>',
            f'  <h3 class="langnote__h3">{esc(L["browse"])}</h3>',
            '  <ul class="langneeds">',
        ]
        for need in NEEDS:
            out.append(f'    <li><a href="{page_for(need["key"])}">'
                       f'{esc(L["needs"][need["key"]])}</a></li>')
        out += [
            '  </ul>',
            f'  <p class="langnote__do"><a class="langnote__go" href="#dir" '
            f'data-lang="{L["key"]}">{esc(L["cta"])}</a>',
            '  <a class="langnote__x" href="#top" lang="en" dir="ltr">Close</a></p>',
            '</section>',
        ]
    return out


def sos_frag(rows, slim=False):
    by_name = {r["Resource Name"]: r for r in rows}
    cls = "sos sos--slim" if slim else "sos"
    out = [f'<section class="{cls}" aria-labelledby="sos-h">',
           '  <h2 id="sos-h" class="sos__h">If you need help right now</h2>',
           '  <ul class="sos__list">',
           '    <li><a href="tel:911"><span class="sos__num">911</span>'
           '<span class="sos__for">You are in danger, or someone is badly hurt</span></a></li>']
    for name, why in SOS:
        r = by_name.get(name)
        if not r:
            raise SystemExit(f"emergency strip: {name!r} is not in the directory")
        kind, label, href = contact(r["Phone"])
        if kind != "call":
            raise SystemExit(f"emergency strip: {name!r} has no dialable number")
        out.append(f'    <li><a href="tel:{esc(href)}"><span class="sos__num">'
                   f'{esc(label)}</span><span class="sos__for">{esc(why)}</span></a></li>')
    out.append('  </ul>')
    if not slim:
        out.append('  <p class="sos__note">These lines are free, and they are answered by '
                   'people trained for exactly this. You can call them without giving '
                   'your name.</p>')
    out.append('</section>')
    return out


def vow_frag():
    return [
        '<section class="vowbox" aria-labelledby="vow-h">',
        '  <h2 id="vow-h">Who we are, and what we will never do</h2>',
        f'  <p class="vowbox__full">{HONESTY}</p>',
        '  <p class="vowbox__src">This is printed on everything we hand out, and said '
        'out loud at every table.</p>',
        '</section>',
    ]


def footer_frag(n, when="recently"):
    return [
        '<footer class="hfoot">',
        '  <div class="hfoot__in">',
        f'    <a class="brand" href="index.html">{PIN}'
        '<span class="brand__txt">Waypoint<small>Student Health Corps</small></span></a>',
        '    <p class="hfoot__say">Waypoint is a student volunteer corps in New York '
        'City. We do not run any of the programs on this page. We help people find '
        'them.</p>',
        '    <ul class="hfoot__links">',
        '      <li><a href="help.html">Find help</a></li>',
        '      <li><a href="index.html">About Waypoint</a></li>',
        '      <li><a href="index.html#students">Volunteer with us</a></li>',
        '      <li><a href="index.html#partners">For organizations</a></li>',
        '      <li><a href="privacy.html">Privacy &amp; legal</a></li>',
        '      <li><a href="mailto:waypointoutreach@gmail.com">waypointoutreach@<wbr />gmail.com</a></li>',
        '    </ul>',
        f'    <p class="hfoot__ver">{n} resources. Last checked {when}. '
        'Programs change &mdash; if something here is wrong, please tell us.</p>',
        '  </div>',
        '</footer>',
        '<script src="help.js" defer></script>',
        '</body>', '</html>',
    ]


def filters_frag(compact=False):
    """The three facets. Identical on the front page and on every category
    page, because a chip that means one thing here and another thing there is
    a chip nobody trusts.

    They live in a disclosure. Nineteen chips is 860px on a phone — three
    screens of chrome between somebody arriving and the first phone number —
    and they are a refinement, not the way in. help.js opens it on a wide
    screen, where the space is free, and leaves it closed on a narrow one.
    The whole block is already script-only (a filter that cannot filter is
    worse than no filter), so nothing is lost when there is no script: the
    disclosure never ships at all.
    """
    out = ['  <details class="find__filters">',
           '    <summary><span>Narrow this list</span></summary>',
           '    <fieldset class="fset"><legend>Where you are</legend><div class="chips">']
    for key, label in BOROUGHS:
        out.append(f'      <button type="button" class="chip" data-f="boro" data-v="{key}" '
                   f'aria-pressed="false">{label}</button>')
    out += ['    </div></fieldset>',
            '    <fieldset class="fset"><legend>Language you speak</legend>',
            '      <p class="fset__hint">Shows places that name your language, and '
            'places that work through interpreters. Ask when you call.</p>',
            '      <div class="chips">']
    for L in LANGUAGES:
        out.append(f'      <button type="button" class="chip" data-f="lang" data-v="{L["key"]}" '
                   f'aria-pressed="false" lang="{L["tag"]}">{esc(L["endonym"])}</button>')
    out += ['    </div></fieldset>',
            '    <fieldset class="fset"><legend>Only show</legend><div class="chips">']
    for key, label in [("free", "Free"), ("open-247", "Open 24/7"),
                       ("no-status", "Does not ask immigration status"),
                       ("phone", "You can call")]:
        out.append(f'      <button type="button" class="chip" data-f="flags" data-v="{key}" '
                   f'aria-pressed="false">{label}</button>')
    out += ['    </div></fieldset>',
            '    <button type="button" class="reset" hidden>Start over</button>',
            '  </details>']
    return out


def search_frag(placeholder, scope_note):
    return [
        '<section class="find" aria-labelledby="find-h" hidden>',
        '  <h2 id="find-h" class="sr-only">Search and narrow the list</h2>',
        '  <div class="find__search">',
        '    <label for="q">Search for what you need</label>',
        '    <div class="find__box">',
        '      <svg class="ico" viewBox="0 0 24 24" aria-hidden="true" fill="none" '
        'stroke="currentColor" stroke-width="1.8" stroke-linecap="round">'
        '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>',
        f'      <input id="q" type="search" autocomplete="off" placeholder="{esc(placeholder)}" />',
        '      <button type="button" class="find__clear" hidden>Clear</button>',
        '    </div>',
        f'    <p class="find__scope">{scope_note}</p>',
        '  </div>',
    ] + filters_frag() + [
        '  <div class="find__foot">',
        '    <p class="find__count" role="status" aria-live="polite"></p>',
        '    <button type="button" class="printbtn" hidden>'
        '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true" fill="none" '
        'stroke="currentColor" stroke-width="1.7" stroke-linecap="round" '
        'stroke-linejoin="round"><path d="M7 9V3h10v6M7 19H5a2 2 0 0 1-2-2v-5a2 2 '
        '0 0 1 2-2h14a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2M7 15h10v6H7v-6Z"/></svg>'
        'Print this list</button>',
        '  </div>',
        '</section>',
    ]


# --------------------------------------------------------------- the pages
# How many resources each cluster shows on the front page before it hands off
# to its own page. Three is the number that fits beside the heading without
# the card becoming a list, and it is enough to show what KIND of thing is
# behind the link — which is the only job a preview has.
PREVIEW = 3

# A lead block is a lead only while it is short. On "I'm not sure where to
# start", thirteen of fifteen resources are marked start-here — every one of
# them genuinely is a place to start — and a Start here block holding the
# whole page tells nobody anything. Past this, the tag goes back to doing what
# it does everywhere else: ordering rows inside their buckets.
LEAD_MAX = 3


def render_preview(r, need_key):
    """One line in a cluster on the front page: the name, what it is for, and
    the number if there is one. No badges, no disclosure — this is a look
    through the door, not the room."""
    a = ['<li class="pv">']
    a.append(f'<a class="pv__n" href="{page_for(need_key)}#r-{esc(need_key)}-{esc(r["_id"])}">'
             f'{esc(r["Resource Name"])}</a>')
    short = r["Description"].split(". ")[0].rstrip(".")
    a.append(f'<p class="pv__d">{esc(short)}.</p>')
    kind, label, href = contact(r["Phone"])
    if kind == "call":
        a.append(f'<a class="pv__call" href="tel:{esc(href)}">'
                 f'<svg class="ico" aria-hidden="true"><use href="#i-phone"/></svg>'
                 f'{esc(label)}</a>')
    elif kind == "text":
        a.append(f'<a class="pv__call" href="{esc(href)}">'
                 f'<svg class="ico" aria-hidden="true"><use href="#i-text"/></svg>'
                 f'{esc(label)}</a>')
    a.append('</li>')
    return "".join(a)


def index_json(rows):
    """The compact index the front page's search runs against.

    The front page no longer carries every resource — that is the whole point
    of splitting the directory into one page per need — so search needs its own
    copy of the facts. Keys are one letter because this ships on every visit
    to the busiest page on the site: at 118 resources it is about 40 KB, and
    it stays roughly linear as the directory grows, which the full markup does
    not.

    It is <script type="application/json">, not a fetch: one round trip fewer
    on the connection this audience actually has, and no failure mode where
    the page renders and the search silently never works.
    """
    out = []
    for r in rows:
        kind, label, href = contact(r["Phone"])
        out.append({
            "i": r["_id"],
            "n": r["Resource Name"],
            "k": r["Subcategory"],
            "d": r["Description"],
            "g": r["_needs"][0],
            "k2": r["_needs"],
            "c": kind,
            "p": label,
            "h": href,
            "w": r["Website"],
            "t": tagtext(r),
            "f": " ".join(r["_flags"]),
            "b": " ".join(r["_boroughs"]),
            "l": " ".join(r["_langs"]),
            "s": haystack(r),
        })
    doc = {
        "needs": {nd["key"]: nd["short"] for nd in NEEDS},
        "page": {nd["key"]: page_for(nd["key"]) for nd in NEEDS},
        # The ten-language query vocabulary, once, keyed by need. Each row
        # carries the need keys it belongs to and help.js composes them.
        "nw": {k: " ".join(v).lower() for k, v in NEED_WORDS.items()},
        "rows": out,
    }
    # `</` inside a JSON string would close the script element early.
    return json.dumps(doc, ensure_ascii=False, separators=(",", ":")) \
               .replace("</", "<\\/")


def render_overview(rows):
    n = len(rows)
    by_need = {need["key"]: ordered(rows, need["key"]) for need in NEEDS}
    p = []
    A = p.append
    p += head("Find free help in New York City — Waypoint",
              "A plain-language directory of free and low-cost help in New York City: "
              "food, medical bills, housing, health care, legal help, and more. Most of "
              "these do not ask about immigration status.",
              "#needs", "Skip to what you need help with")
    p += header_frag()
    A('<main class="wrap">')
    p += langbar_frag()

    # ---- masthead
    A('<section class="mast">')
    A('  <div class="mast__bg" aria-hidden="true"></div>')
    A('  <span class="eyebrow mast__eye">Waypoint &middot; New York City</span>')
    A('  <h1>Find free help <em>in New York City.</em></h1>')
    A(f'  <p class="mast__say">This is a list of <b>{n} places</b> that help New '
      'Yorkers with food, medical bills, housing, health care, legal problems and '
      'more. Nearly all of them are free. Most do not ask about immigration status.</p>')
    A('  <p class="mast__say mast__say--2">You do not need an account. You do not '
      'need to tell us anything. Pick what you need below, and call them yourself.</p>')
    A('</section>')

    # Attribution, for paper only. A printed sheet with no source on it is a
    # photocopy of nothing, and this one gets handed to people at a table.
    A('<div class="printhead" aria-hidden="true">')
    A('  <p class="printhead__s">Collected by Waypoint, a student volunteer '
      'corps. We do not run any of these programs &mdash; we help people find '
      f'them. Checked {checked(rows)}; programs change. Every one of these '
      'headings has a page of its own with more places on it.</p>')
    A('</div>')

    p += sos_frag(rows)
    A('<hr class="rule" />')

    A('<noscript><p class="noscript-note">Search needs JavaScript, which is turned '
      'off. Nothing is lost: every heading below opens a page '
      'with all of that kind of help on it, and every phone number on this page '
      'dials.</p></noscript>')
    p += search_frag("Try: food, rent, dentist, lawyer",
                     "Searches all " + str(n) + " places, not just the ones shown below.")

    # ---- search results (built by help.js from the index below; empty until then)
    A('<section class="results" id="results" hidden aria-labelledby="results-h">')
    A('  <h2 id="results-h" class="results__h"></h2>')
    A('  <ul class="rows" id="resultRows"></ul>')
    A('  <p class="dir__none" hidden>Nothing here matched that. Try a different word, '
      'or <button type="button" class="linkish reset">show everything again</button>. '
      'If you cannot find it, call <a href="tel:311">311</a> &mdash; they will point '
      'you somewhere, in your language, at any hour.</p>')
    A('</section>')

    # ---- the clusters
    A('<div class="clusters" id="needs">')
    A('  <div class="clusters__head">')
    A('    <h2 id="needs-h">What do you need help with?</h2>')
    # No count in this sentence. It said "Fifteen kinds of help" and there
    # were sixteen by the time anyone looked, which is what every number
    # written into prose eventually does. The grid below is the count.
    A('    <p class="clusters__say">Each one shows a few places, and opens a '
      'page with all of them.</p>')
    A('  </div>')
    A('  <nav class="jump" aria-label="Jump to a kind of help"><ul>')
    for need in NEEDS:
        A(f'    <li><a href="#n-{need["key"]}">{esc(need["short"])}</a></li>')
    A('  </ul></nav>')
    A('  <ul class="clusters__grid">')
    for need in NEEDS:
        group = by_need[need["key"]]
        c = len(group)
        A(f'  <li><section class="cl" id="n-{need["key"]}" data-need="{need["key"]}" '
          f'aria-labelledby="h-{need["key"]}">')
        A('    <div class="cl__head">')
        A(f'      {icon(need["icon"])}')
        A('      <div>')
        A(f'        <h3 id="h-{need["key"]}"><a href="{page_for(need["key"])}">'
          f'{esc(need["label"])}</a></h3>')
        A(f'        <p class="cl__b">{esc(need["blurb"])}</p>')
        A('      </div>')
        A('    </div>')
        A('    <ul class="cl__pv">')
        for r in group[:PREVIEW]:
            A("      " + render_preview(r, need["key"]))
        A('    </ul>')
        rest = max(0, c - PREVIEW)
        more = (f'See all {c} places' if rest else
                (f'See {"this place" if c == 1 else f"all {c} places"}'))
        A(f'    <a class="cl__all" href="{page_for(need["key"])}">{more} '
          f'<span class="arr">&rarr;</span></a>')
        A('  </section></li>')
    A('  </ul>')
    A('</div>')

    p += vow_frag()
    A('</main>')
    A(f'<script type="application/json" id="ix">{index_json(rows)}</script>')
    p += footer_frag(n, checked(rows))
    return "\n".join(p) + "\n"


def render_category(need, rows):
    """One kind of help, on its own page: a rail you can skim, the resources
    broken into buckets, and every neighbouring kind of help one tap away."""
    key = need["key"]
    group = ordered(rows, key)
    n_all = len(rows)

    # Everything on this page is bucketed by subject, whether it got here
    # through its own category or through a keyword.
    #
    # These used to be two sections, with cross-references collected at the
    # bottom under "Also worth calling". That was honest and it was wrong: on
    # a need that cuts across everything — a disability page is 5 resources of
    # its own and 21 that answer it from somewhere else — the page became five
    # rows and then a heap. And it was wrong even where it looked fine:
    # somebody on "I got a medical bill" looking for insurance enrolment wants
    # it under "Getting covered in the first place", not in an appendix.
    #
    # What is kept is the ordering. Inside a bucket, the resources whose own
    # category is this need come first, so the bill experts still lead the bill
    # page. The row's own subcategory line already says what each thing is.
    primary = [r for r in group if key in [nd["key"] for nd in NEEDS
                                           if r["Category"] in nd.get("cats", [])]]
    own = {id(r) for r in primary}

    # The best first call leads the page, in its own block, before any
    # bucket. `start-here` is a tag in the data on the row that is genuinely
    # the right opening move for this need, and burying it three headings down
    # because it happens to be filed under "money for the rent" is exactly the
    # mistake the tag exists to prevent. It appears once: here, not also in
    # its topical bucket.
    # A lead block is a lead only while it is short. On "I'm not sure where to
    # start", thirteen of fifteen resources are marked start-here — every one
    # of them genuinely is a place to start — and a Start here block holding
    # the whole page tells nobody anything. Past three, the tag goes back to
    # doing what it does everywhere else: ordering rows inside their buckets.
    lead = [r for r in primary if "start-here" in r["Tags"]]
    if len(lead) > LEAD_MAX:
        lead = []
    rest = [r for r in group if r not in lead]

    buckets = [(bk, prose(lb), w) for bk, lb, w in
               GROUPS.get(key, [("more", "Places that help", [])])]
    filed = {b[0]: [] for b in buckets}
    for r in rest:
        filed[group_for(r, key)].append(r)
    for bk in filed:
        filed[bk].sort(key=lambda r: (0 if "start-here" in r["Tags"] else 1,
                                      0 if id(r) in own else 1))
    live = [(bk, label) for bk, label, _ in buckets if filed[bk]]
    if lead:
        live = [("lead", "Start here" if len(lead) == 1
                 else "Start here \u2014 the first calls to make")] + live
        filed["lead"] = lead

    p = []
    A = p.append
    p += head(f'{need["label"]} — free help in New York City | Waypoint',
              need["seo"],
              "#dir", "Skip to the list")
    p += header_frag()
    A('<main class="wrap">')
    A('<nav class="crumb" aria-label="Breadcrumb"><a href="help.html">'
      '<span class="arr crumb__back" aria-hidden="true">&larr;</span> All free help</a>'
      f'<span class="crumb__sep" aria-hidden="true">/</span><span aria-current="page">'
      f'{esc(need["short"])}</span></nav>')
    p += langbar_frag()

    A('<section class="mast mast--cat">')
    A('  <div class="mast__bg" aria-hidden="true"></div>')
    A('  <span class="eyebrow mast__eye">Waypoint &middot; Free help in New York City</span>')
    A(f'  <h1>{esc(need["h1a"])} <em>{esc(need["h1b"])}</em></h1>')
    A(f'  <p class="mast__say">{esc(need["intro"])}</p>')
    A(f'  <p class="mast__say mast__say--2"><b>{len(group)} '
      f'{"place" if len(group) == 1 else "places"}</b> on this page. Nearly all are '
      'free. Most do not ask about immigration status. You can call them yourself &mdash; '
      'you do not have to go through us.</p>')
    A('</section>')

    p += sos_frag(rows, slim=True)

    A('<noscript><p class="noscript-note">Search and filtering need JavaScript, which '
      'is turned off. Everything is still here: every place on this page is listed '
      'below, in labelled groups, and every phone number dials.</p></noscript>')

    A('<div class="cat">')
    # ---- the rail
    A('<aside class="cat__rail" aria-labelledby="rail-h">')
    A('  <h2 id="rail-h" class="rail__h">On this page</h2>')
    A('  <nav class="rail__nav" aria-label="Sections of this page"><ul>')
    for bk, label in live:
        A(f'    <li><a href="#g-{key}-{bk}"><span class="rail__t">{esc(label)}'
          f'</span><span class="rail__n">{len(filed[bk])}</span></a></li>')
    A('  </ul></nav>')
    A('</aside>')

    A('<div class="cat__main">')
    p += search_frag(esc(need["ph"]), "Searches the " + str(len(group)) +
                     " places on this page.")
    A('<div class="printhead" aria-hidden="true">')
    A(f'  <p class="printhead__t">{esc(need["label"])}</p>')
    A('  <p class="printhead__s">Collected by Waypoint, a student volunteer '
      'corps. We do not run any of these programs &mdash; we help people find '
      f'them. Checked {checked(rows)}; programs change.</p>')
    A('</div>')
    A(f'<div class="dir" id="dir" data-nw="{esc(needwords([key]))}">')
    A('<p class="dir__none" hidden>Nothing here matched that. Try a different word, or '
      '<button type="button" class="linkish reset">show everything again</button>. '
      'If you cannot find it, call <a href="tel:311">311</a> &mdash; they will point '
      'you somewhere, in your language, at any hour.</p>')
    for bk, label in live:
        cls = "grp grp--lead" if bk == "lead" else "grp"
        A(f'<section class="{cls}" id="g-{key}-{bk}" data-need="{key}" '
          f'aria-labelledby="gh-{key}-{bk}">')
        A('  <div class="grp__head">')
        A(f'    <h2 id="gh-{key}-{bk}">{esc(label)}</h2>')
        A('    <a class="grp__top" href="#top">Back to the top</a>')
        A('  </div>')
        A('  <ul class="rows">')
        for r in filed[bk]:
            A(render_row(r, key))
        A('  </ul>')
        A('</section>')
    A('</div>')

    # ---- neighbours
    A('<nav class="sibs" aria-labelledby="sibs-h">')
    A('  <h2 id="sibs-h">Something else?</h2>')
    A('  <ul>')
    for other in NEEDS:
        if other["key"] == key:
            continue
        c = len(ordered(rows, other["key"]))
        A(f'    <li><a href="{page_for(other["key"])}">{icon(other["icon"])}'
          f'<span class="sibs__t">{esc(other["label"])}</span>'
          f'<span class="sibs__n">{c}</span></a></li>')
    A('  </ul>')
    A(f'  <p class="sibs__all"><a href="help.html">Back to all {n_all} places '
      '<span class="arr">&rarr;</span></a></p>')
    A('</nav>')
    A('</div>')   # cat__main
    A('</div>')   # cat

    p += vow_frag()
    A('</main>')
    p += footer_frag(n_all, checked(rows))
    return "\n".join(p) + "\n"


def selfcheck():
    """The phone parser, which is the one place here where being wrong hurts
    somebody: a number that does not dial on a crisis line is worse than no
    button at all. Run by every build."""
    cases = [
        # cell                                    kind     label            href
        ("917-720-9700",                          "call", "917-720-9700",  "+19177209700"),
        ("800-621-4673 (800-621-HOPE); TTY 866-604-5350",
                                                  "call", "800-621-4673",  "+18006214673"),
        ("311 (or 212-639-9675)",                 "call", "311",           "311"),
        # the one that mattered: naive digit-stripping gave +19881838255
        ("988 then press 1 / text 838255",        "call", "988",           "988"),
        ("Text HOME to 741741",                   "text", "Text HOME to 741741", "sms:741741"),
        ("800-786-2929 (1-800-RUNAWAY)",          "call", "800-786-2929",  "+18007862929"),
        ("1-800-273-8255",                        "call", "1-800-273-8255","+18002738255"),
        ("",                                      "none", "",              ""),
        ("see website",                           "none", "",              ""),
    ]
    for cell, kind, label, href in cases:
        got = contact(cell)
        assert got == (kind, label, href), f"contact({cell!r}) -> {got}, wanted {(kind, label, href)}"

    # every dialable href is either a short code or a full +1 number: anything
    # in between is a number that will not connect.
    for r in load():
        kind, label, href = contact(r["Phone"])
        if kind == "call":
            assert re.fullmatch(r"\+1[0-9]{10}|[0-9]{3}", href), \
                f"{r['Resource Name']}: unusable tel: {href!r} from {r['Phone']!r}"


HOME = ROOT / "index.html"


def home_links():
    """The one block of index.html this build owns.

    The narrative page is hand-written and stays that way. But its list of
    what the directory holds is not prose — it is the directory's own table of
    contents, rendered on the other side of the site, and hand-maintaining it
    meant it offered eight of sixteen kinds of help for as long as nobody
    looked. Generated from NEEDS, like everything else that has to agree with
    NEEDS.
    """
    return ("      <ul class=\"helplinks\">\n"
            + "\n".join(f'        <li><a href="{page_for(n["key"])}">'
                        f'{esc(n["label"])}</a></li>' for n in NEEDS)
            + "\n      </ul>")


def sync_home():
    src = HOME.read_text(encoding="utf-8")
    block = re.search(r'      <ul class="helplinks">.*?</ul>', src, re.S)
    if not block:
        raise SystemExit("index.html: no helplinks list to keep in step with NEEDS")
    fresh = src.replace(block.group(0), home_links(), 1)
    if fresh != src:
        HOME.write_text(fresh, encoding="utf-8")
        return True
    return False


def build():
    """Write the front page and one page per need.

    Splitting the directory was not cosmetic. One page carrying every resource
    was 250 KB of markup and sixteen headings deep, and the person it is for
    opens it frightened, on a phone, looking for one phone number. Now the
    front page is a way in — one cluster per need, three examples each — and each
    kind of help gets a page built to be skimmed: a rail of what is on it,
    resources in named buckets rather than one run of forty, and every
    neighbouring kind of help one tap away.

    Nothing about the contract changed: every page is static HTML with every
    resource in it, every phone number is a real tel: link, and JavaScript
    only ever hides rows that are already there.
    """
    rows = load()
    written = []

    overview = ROOT / "help.html"
    overview.write_text(render_overview(rows), encoding="utf-8")
    written.append(overview)

    for need in NEEDS:
        path = ROOT / page_for(need["key"])
        path.write_text(render_category(need, rows), encoding="utf-8")
        written.append(path)
    if sync_home():
        print("updated index.html's list of what the directory holds")
    return rows, written


if __name__ == "__main__":
    selfcheck()
    print("selfcheck ok")
    rows = load()
    print(f"{len(rows)} resources")
    from collections import Counter
    c = Counter(n for r in rows for n in r["_needs"])
    for need in NEEDS:
        print(f'  {c[need["key"]]:3}  {need["label"]}')
    print(f'  urgent: {sum(1 for r in rows if r["_urgent"])}')

    # Where the catch-all buckets are swallowing a category. A "More places
    # that help" holding half the page means the buckets above it are wrong,
    # and this is the only place that would ever say so.
    stuffed = []
    for need in NEEDS:
        grp = ordered(rows, need["key"])
        primary = [r for r in grp
                   if need["key"] in [nd["key"] for nd in NEEDS
                                      if r["Category"] in nd.get("cats", [])]]
        if not primary:
            continue
        last = GROUPS[need["key"]][-1][0]
        n_last = sum(1 for r in primary if group_for(r, need["key"]) == last)
        if n_last > max(2, len(primary) * 0.34):
            stuffed.append(f'{need["key"]}: {n_last}/{len(primary)} fell through to '
                           f'"{GROUPS[need["key"]][-1][1]}"')
    if stuffed:
        print("BUCKETS TOO COARSE:", file=sys.stderr)
        for s in stuffed:
            print("   ", s, file=sys.stderr)

    # What each cross-reference keyword actually drags in. A keyword that pulls
    # a third of the directory onto a page is a keyword that is matching
    # something other than what it meant to.
    greedy = []
    for need in NEEDS:
        for kw in need.get("also", []):
            hit = [r for r in rows
                   if need["key"] not in [nd["key"] for nd in NEEDS
                                          if r["Category"] in nd.get("cats", [])]
                   and _fires(kw, (r["Subcategory"] + " " + r["Resource Name"]).lower())]
            if len(hit) > 12:
                greedy.append(f'{need["key"]}/"{kw}" pulls in {len(hit)} rows, '
                              f'e.g. {hit[0]["Resource Name"]!r}')
    if greedy:
        print("CROSS-REFERENCE KEYWORD TOO BROAD:", file=sys.stderr)
        for g in greedy:
            print("   ", g, file=sys.stderr)

    # A bucket whose rule matches nothing is usually a rule that rotted when
    # a label was reworded, not a kind of help nobody offers. Rewording the
    # subcategories once left nine of them dead and it took a distribution
    # dump to see it.
    dead = []
    for need in NEEDS:
        grp = ordered(rows, need["key"])
        for bk, label, words in GROUPS.get(need["key"], []):
            if not words:
                continue
            if not any(group_for(r, need["key"]) == bk for r in grp):
                dead.append(f'{need["key"]}/{bk} ("{label}") matches nothing')
    if dead:
        print("BUCKET RULE MATCHES NOTHING:", file=sys.stderr)
        for d in dead:
            print("   ", d, file=sys.stderr)

    missing = [r["Resource Name"] for r in rows
               if contact(r["Phone"])[0] == "none" and not r["Website"]]
    unparsed = [(r["Resource Name"], r["Phone"]) for r in rows
                if r["Phone"] and contact(r["Phone"])[0] == "none"]
    if unparsed:
        print("PHONE NOT PARSED:", unparsed, file=sys.stderr)
    if missing:
        print("NO WAY TO REACH:", missing, file=sys.stderr)

    _, written = build()
    total = sum(p.stat().st_size for p in written) / 1024
    front = written[0].stat().st_size / 1024
    print(f"wrote {len(written)} pages, {total:.0f} KB total "
          f"({written[0].name} {front:.0f} KB)")
