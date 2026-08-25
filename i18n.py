"""Every word of the site's own chrome, in the ten languages Local Law 30 names.

This is the file a translator gets handed. It is data, not logic: build_help.py
renders exactly the same page from it that it renders in English, so a language
page is not a notice about the English page — it is the page.

What is NOT here, and why. The 340 resources keep their own names, phone
numbers and addresses: an organisation's name is a proper noun and its number
is a number, and both are what somebody has to say and dial. Their English
descriptions are not translated either, and rather than print them under a
translated heading every language page carries `english`, one plain sentence
saying the detail pages are in English and that 311 will put an interpreter on
the line for free, at any hour.

Every string here was written for this site rather than converted from the
English word by word: "I need food" is a sentence somebody would actually say,
and so is `comida` and so is 「我需要食物」. The register is the same as the
English — short sentences, ordinary words, no agency vocabulary.

STILL NEEDS A HUMAN: a native speaker of each language should read their own
page end to end. Nothing here is machine output, but nothing here has been read
by somebody who speaks the language either.
"""

# Order matches LANGUAGES in build_help.py. Keys:
#
#   nav        the five header tabs, in the header's order
#   eyebrow    the line above the masthead title
#   title_a    the masthead title, roman half
#   title_b    ... and the emphasised half (gold; italic only where the script
#              has a real italic — see build_help.EMPHASIS)
#   lede1/2    the two masthead paragraphs; {n} is the resource count
#   sos_h      heading of the emergency panel
#   sos        the four numbers' "this is for" lines, in panel order
#   sos_note   the line under them
#   english    the one sentence about what is and is not in this language
#   needs_h    heading over the seventeen cards
#   needs_sub  the line under it
#   open_all   the link at the foot of a card; {n} is that need's count
#   vow_h      heading of the honesty statement
#   vow        the honesty statement itself — a promise, so it is translated
#              whole and never summarised
#   vow_src    the line under it
#   foot_say   what Waypoint is
#   foot_links five footer links, in the footer's order
#   foot_ver   {n} resources, {when} the checked span
#   langbar_h  heading over the language chips
#   english_h  heading of the English-pages note
#   skip       the skip link
#   here       marks the language you are already reading

UI = {}

UI["spanish"] = {
    "nav": ["Buscar ayuda", "Facturas y rechazos", "Cómo funciona",
            "Estudiantes", "Organizaciones"],
    "eyebrow": "Waypoint · Ciudad de Nueva York",
    "title_a": "Ayuda gratuita",
    "title_b": "en la ciudad de Nueva York.",
    "lede1": "Esta es una lista de {n} lugares que ayudan a los neoyorquinos "
             "con comida, facturas médicas, vivienda, atención médica, "
             "problemas legales y más. Casi todos son gratis. La mayoría no "
             "pregunta por su situación migratoria.",
    "lede2": "No necesita crear una cuenta. No tiene que contarnos nada. "
             "Elija abajo lo que necesita y llame usted mismo.",
    "sos_h": "Si necesita ayuda ahora mismo",
    "sos": ["Está en peligro, o alguien está gravemente herido",
            "No se siente seguro consigo mismo, o necesita hablar con alguien ahora",
            "Alguien en su casa o su pareja le hace daño o le da miedo",
            "Cualquier otra cosa. Gratis, a cualquier hora, en su idioma"],
    "sos_note": "Estas líneas son gratuitas y las contestan personas "
                "preparadas para exactamente esto. Puede llamar sin dar su nombre.",
    "english": "Las páginas de cada tema están en inglés. Llame al 311 y pida "
               "un intérprete de español: es gratis, a cualquier hora, y se "
               "queda en la llamada con usted.",
    "needs_h": "¿Con qué necesita ayuda?",
    "needs_sub": "Cada uno muestra algunos lugares y abre una página con todos.",
    "open_all": "Ver los {n}",
    "vow_h": "Quiénes somos, y lo que nunca haremos",
    "vow": "Somos estudiantes voluntarios con formación. Le ayudamos a "
           "encontrar los programas gratuitos y los profesionales de Nueva "
           "York que se ocupan de facturas médicas y rechazos del seguro. No "
           "somos médicos, abogados, asesores de beneficios ni expertos en "
           "seguros. No leemos sus facturas, no llenamos sus formularios y no "
           "le decimos a qué tiene derecho. Le ponemos en contacto con quienes "
           "sí hacen eso, y lo hacen gratis. Nunca cobramos nada.",
    "vow_src": "Esto está impreso en todo lo que repartimos y se dice en voz "
               "alta en cada mesa.",
    "foot_say": "Waypoint es un cuerpo de estudiantes voluntarios de la ciudad "
                "de Nueva York. No dirigimos ninguno de los programas de esta "
                "página. Ayudamos a la gente a encontrarlos.",
    "foot_links": ["Buscar ayuda", "Sobre Waypoint", "Ser voluntario",
                   "Para organizaciones", "Privacidad y aviso legal"],
    "foot_ver": "{n} recursos. Última comprobación: {when}. Los programas "
                "cambian: si algo aquí está mal, díganoslo.",
    "langbar_h": "Reciba ayuda en su idioma",
    "english_h": "Sobre el idioma",
    "home": 'Waypoint, página principal',
    "nav_label": 'Navegación principal',
    "skip": "Ir a la lista",
    "here": "está leyendo esta página",
}

UI["french"] = {
    "nav": ["Trouver de l’aide", "Factures et refus", "Comment ça marche",
            "Étudiants", "Organismes"],
    "eyebrow": "Waypoint · New York",
    "title_a": "De l’aide gratuite",
    "title_b": "à New York.",
    "lede1": "Voici une liste de {n} endroits qui aident les New-Yorkais pour "
             "la nourriture, les factures médicales, le logement, les soins, "
             "les problèmes juridiques et bien d’autres choses. Presque tout "
             "est gratuit. La plupart ne demandent pas votre statut migratoire.",
    "lede2": "Pas besoin de créer un compte. Vous n’avez rien à nous dire. "
             "Choisissez ci-dessous ce dont vous avez besoin et appelez vous-même.",
    "sos_h": "Si vous avez besoin d’aide tout de suite",
    "sos": ["Vous êtes en danger, ou quelqu’un est gravement blessé",
            "Vous ne vous sentez pas en sécurité avec vous-même, ou vous avez "
            "besoin de parler à quelqu’un maintenant",
            "Quelqu’un chez vous ou votre partenaire vous fait du mal ou vous fait peur",
            "Tout le reste. Gratuit, à toute heure, dans votre langue"],
    "sos_note": "Ces lignes sont gratuites et répondues par des personnes "
                "formées pour exactement cela. Vous pouvez appeler sans donner votre nom.",
    "english": "Les pages de chaque sujet sont en anglais. Appelez le 311 et "
               "demandez un interprète en français : c’est gratuit, à toute "
               "heure, et l’interprète reste en ligne avec vous.",
    "needs_h": "De quoi avez-vous besoin ?",
    "needs_sub": "Chaque carte montre quelques endroits et ouvre une page avec tous.",
    "open_all": "Voir les {n}",
    "vow_h": "Qui nous sommes, et ce que nous ne ferons jamais",
    "vow": "Nous sommes des étudiants bénévoles formés. Nous vous aidons à "
           "trouver les programmes gratuits et les professionnels de New York "
           "qui s’occupent des factures médicales et des refus d’assurance. "
           "Nous ne sommes ni médecins, ni avocats, ni conseillers en "
           "prestations, ni experts en assurance. Nous ne lisons pas vos "
           "factures, nous ne remplissons pas vos formulaires et nous ne vous "
           "disons pas à quoi vous avez droit. Nous vous mettons en contact "
           "avec ceux qui le font, et ils le font gratuitement. Nous ne "
           "facturons jamais rien.",
    "vow_src": "C’est imprimé sur tout ce que nous distribuons et dit à voix "
               "haute à chaque table.",
    "foot_say": "Waypoint est un corps d’étudiants bénévoles de la ville de "
                "New York. Nous ne gérons aucun des programmes de cette page. "
                "Nous aidons les gens à les trouver.",
    "foot_links": ["Trouver de l’aide", "À propos de Waypoint", "Devenir bénévole",
                   "Pour les organismes", "Confidentialité et mentions légales"],
    "foot_ver": "{n} ressources. Dernière vérification : {when}. Les programmes "
                "changent — si quelque chose ici est faux, dites-le-nous.",
    "langbar_h": "De l’aide dans votre langue",
    "english_h": "À propos de la langue",
    "home": 'Waypoint, page d’accueil',
    "nav_label": 'Navigation principale',
    "skip": "Aller à la liste",
    "here": "vous lisez cette page",
}

UI["polish"] = {
    # Register: impersonal and direct, the way Polish public-service and
    # helpline copy is actually written. The first draft used "Pani ani Pan"
    # to stay formal and gender-neutral at once, which made every sentence
    # heavier than the English it came from and read like a form.
    "nav": ["Znajdź pomoc", "Rachunki i odmowy", "Jak to działa",
            "Studenci", "Organizacje"],
    "eyebrow": "Waypoint · Nowy Jork",
    "title_a": "Bezpłatna pomoc",
    "title_b": "w Nowym Jorku.",
    "lede1": "To lista {n} miejsc, które pomagają mieszkańcom Nowego Jorku w "
             "sprawach jedzenia, rachunków za leczenie, mieszkania, opieki "
             "zdrowotnej, spraw prawnych i wielu innych. Prawie wszystko jest "
             "za darmo. Większość nie pyta o status imigracyjny.",
    "lede2": "Nie trzeba zakładać konta. Nie trzeba nam nic mówić. Wystarczy "
             "wybrać poniżej to, czego potrzebujesz, i zadzwonić samemu.",
    "sos_h": "Jeśli potrzebujesz pomocy teraz",
    "sos": ["Jesteś w niebezpieczeństwie albo ktoś jest ciężko ranny",
            "Nie czujesz się bezpiecznie ze sobą albo musisz z kimś "
            "porozmawiać właśnie teraz",
            "Ktoś w domu albo partner rani cię lub straszy",
            "Wszystko inne. Za darmo, o każdej porze, w twoim języku"],
    "sos_note": "Te linie są bezpłatne, a odbierają je osoby przeszkolone "
                "dokładnie do tego. Można zadzwonić bez podawania nazwiska.",
    "english": "Strony poszczególnych tematów są po angielsku. Zadzwoń pod "
               "311 i poproś o tłumacza języka polskiego — to bezpłatne, o "
               "każdej porze, a tłumacz zostaje na linii przez całą rozmowę.",
    "needs_h": "W czym potrzebujesz pomocy?",
    "needs_sub": "Każda karta pokazuje kilka miejsc i otwiera stronę ze wszystkimi.",
    "open_all": "Zobacz wszystkie ({n})",
    "vow_h": "Kim jesteśmy i czego nigdy nie zrobimy",
    "vow": "Jesteśmy przeszkolonymi studentami-wolontariuszami. Pomagamy "
           "znaleźć bezpłatne programy i specjalistów w Nowym Jorku, którzy "
           "zajmują się rachunkami za leczenie i odmowami ubezpieczenia. Nie "
           "jesteśmy lekarzami, prawnikami, doradcami do spraw świadczeń ani "
           "ekspertami od ubezpieczeń. Nie czytamy twoich rachunków, nie "
           "wypełniamy formularzy i nie mówimy, co ci przysługuje. Łączymy cię "
           "z osobami, które to robią — i robią to za darmo. Nigdy za nic nie "
           "pobieramy opłat.",
    "vow_src": "To jest wydrukowane na wszystkim, co rozdajemy, i mówione na "
               "głos przy każdym stoliku.",
    "foot_say": "Waypoint to grupa studentów-wolontariuszy z Nowego Jorku. Nie "
                "prowadzimy żadnego z programów na tej stronie. Pomagamy "
                "ludziom je znaleźć.",
    "foot_links": ["Znajdź pomoc", "O Waypoint", "Zostań wolontariuszem",
                   "Dla organizacji", "Prywatność i informacje prawne"],
    "foot_ver": "{n} zasobów. Ostatnio sprawdzone: {when}. Programy się "
                "zmieniają — jeśli coś tu jest nieaktualne, daj nam znać.",
    "langbar_h": "Pomoc w twoim języku",
    "english_h": "O języku",
    "home": 'Waypoint, strona główna',
    "nav_label": 'Nawigacja główna',
    "skip": "Przejdź do listy",
    "here": "czytasz tę stronę",
}

UI["haitian-creole"] = {
    "nav": ["Jwenn èd", "Bòdwo ak refi", "Kijan sa mache",
            "Etidyan", "Òganizasyon"],
    "eyebrow": "Waypoint · Vil Nouyòk",
    "title_a": "Èd gratis",
    "title_b": "nan Vil Nouyòk.",
    "lede1": "Sa se yon lis {n} kote ki ede moun Nouyòk ak manje, bòdwo "
             "doktè, kote pou rete, swen sante, pwoblèm legal ak lòt bagay "
             "ankò. Prèske tout gratis. Pifò pa mande estati imigrasyon ou.",
    "lede2": "Ou pa bezwen louvri yon kont. Ou pa bezwen di nou anyen. Chwazi "
             "sa ou bezwen anba a, epi rele yo ou menm.",
    "sos_h": "Si ou bezwen èd kounye a",
    "sos": ["Ou an danje, oswa yon moun blese grav",
            "Ou pa santi ou an sekirite ak tèt ou, oswa ou bezwen pale ak yon "
            "moun kounye a",
            "Yon moun lakay ou oswa patnè ou ap fè ou mal oswa ap fè ou pè",
            "Nenpòt lòt bagay. Gratis, nenpòt lè, nan lang ou"],
    "sos_note": "Liy sa yo gratis, epi se moun ki fòme espesyalman pou sa ki "
                "reponn. Ou ka rele san bay non ou.",
    "english": "Paj chak sijè yo an anglè. Rele 311 epi mande yon entèprèt "
               "kreyòl ayisyen — li gratis, nenpòt lè, epi entèprèt la rete "
               "nan telefòn nan avè ou.",
    "needs_h": "Ki sa ou bezwen èd pou li?",
    "needs_sub": "Chak kat montre kèk kote epi louvri yon paj ak tout.",
    "open_all": "Gade tout {n} yo",
    "vow_h": "Ki moun nou ye, epi sa nou p ap janm fè",
    "vow": "Nou se etidyan volontè ki fòme. Nou ede ou jwenn pwogram gratis ak "
           "pwofesyonèl nan Nouyòk ki okipe bòdwo doktè ak refi asirans. Nou "
           "pa doktè, nou pa avoka, nou pa konseye benefis, epi nou pa ekspè "
           "asirans. Nou pa li bòdwo ou, nou pa ranpli fòm ou, epi nou pa di "
           "ou pou ki sa ou kalifye. Nou konekte ou ak moun ki fè sa, epi yo "
           "fè li gratis. Nou pa janm mande lajan pou anyen.",
    "vow_src": "Sa enprime sou tout sa nou bay, epi nou di li byen fò nan chak tab.",
    "foot_say": "Waypoint se yon gwoup etidyan volontè nan Vil Nouyòk. Nou pa "
                "dirije okenn nan pwogram ki sou paj sa a. Nou ede moun jwenn yo.",
    "foot_links": ["Jwenn èd", "Sou Waypoint", "Vin volontè",
                   "Pou òganizasyon", "Konfidansyalite ak legal"],
    "foot_ver": "{n} resous. Dènye verifikasyon: {when}. Pwogram yo chanje — "
                "si gen yon bagay ki pa kòrèk isit la, tanpri di nou.",
    "langbar_h": "Jwenn èd nan lang ou",
    "english_h": "Sou lang lan",
    "home": 'Waypoint, paj dakèy',
    "nav_label": 'Navigasyon prensipal',
    "skip": "Ale nan lis la",
    "here": "w ap li paj sa a",
}

UI["russian"] = {
    "nav": ["Найти помощь", "Счета и отказы", "Как это работает",
            "Студентам", "Организациям"],
    "eyebrow": "Waypoint · Нью-Йорк",
    "title_a": "Бесплатная помощь",
    "title_b": "в Нью-Йорке.",
    "lede1": "Это список из {n} мест, где помогают жителям Нью-Йорка с едой, "
             "счетами за лечение, жильём, медицинской помощью, юридическими "
             "вопросами и не только. Почти всё бесплатно. Большинство не "
             "спрашивает об иммиграционном статусе.",
    "lede2": "Не нужно заводить учётную запись. Не нужно ничего нам "
             "рассказывать. Выберите ниже то, что вам нужно, и позвоните сами.",
    "sos_h": "Если помощь нужна прямо сейчас",
    "sos": ["Вы в опасности или кто-то тяжело пострадал",
            "Вам небезопасно наедине с собой или нужно с кем-то поговорить прямо сейчас",
            "Кто-то дома или партнёр причиняет вам боль или пугает вас",
            "Всё остальное. Бесплатно, в любое время, на вашем языке"],
    "sos_note": "Эти линии бесплатные, и на них отвечают люди, обученные "
                "именно этому. Звонить можно, не называя своего имени.",
    "english": "Страницы по каждой теме — на английском. Позвоните по номеру "
               "311 и попросите переводчика на русский язык: это бесплатно, в "
               "любое время, и переводчик остаётся на линии вместе с вами.",
    "needs_h": "С чем нужна помощь?",
    "needs_sub": "На каждой карточке — несколько мест, а по ссылке открывается "
                 "страница со всеми.",
    "open_all": "Показать все ({n})",
    "vow_h": "Кто мы такие и чего мы никогда не делаем",
    "vow": "Мы — обученные студенты-волонтёры. Мы помогаем найти бесплатные "
           "программы и специалистов в Нью-Йорке, которые занимаются счетами "
           "за лечение и отказами страховых компаний. Мы не врачи, не юристы, "
           "не консультанты по пособиям и не специалисты по страхованию. Мы не "
           "читаем ваши счета, не заполняем за вас бланки и не говорим, на что "
           "вы имеете право. Мы связываем вас с теми, кто это делает, — и они "
           "делают это бесплатно. Мы никогда ни за что не берём денег.",
    "vow_src": "Это напечатано на всём, что мы раздаём, и произносится вслух "
               "за каждым столом.",
    "foot_say": "Waypoint — это студенческий волонтёрский корпус в Нью-Йорке. "
                "Мы не ведём ни одну из программ на этой странице. Мы помогаем "
                "людям их найти.",
    "foot_links": ["Найти помощь", "О Waypoint", "Стать волонтёром",
                   "Для организаций", "Конфиденциальность и правовая информация"],
    "foot_ver": "{n} ресурсов. Последняя проверка: {when}. Программы меняются "
                "— если здесь что-то не так, сообщите нам.",
    "langbar_h": "Помощь на вашем языке",
    "english_h": "О языке",
    "home": 'Waypoint, главная страница',
    "nav_label": 'Основная навигация',
    "skip": "Перейти к списку",
    "here": "вы читаете эту страницу",
}

UI["chinese"] = {
    "nav": ["寻找帮助", "医疗账单与拒赔", "服务流程", "学生", "合作机构"],
    "eyebrow": "Waypoint · 纽约市",
    "title_a": "纽约市的",
    "title_b": "免费帮助。",
    "lede1": "这里列出 {n} 家机构，为纽约市民提供食物、医疗账单、住房、"
             "医疗照护、法律问题等方面的帮助。几乎全部免费。大多数机构"
             "不会询问您的移民身份。",
    "lede2": "不需要注册账号，也不需要向我们说明任何情况。在下面选择您"
             "需要的类别，然后自己打电话联系。",
    "sos_h": "如果您现在就需要帮助",
    "sos": ["您有危险，或者有人受了重伤",
            "您担心自己的安全，或者现在想找人倾诉",
            "家里的人或伴侣正在伤害您、让您害怕",
            "其他任何情况。免费，任何时间，可用您的语言"],
    "sos_note": "这些电话免费，接听的人都受过专门训练。您可以不报姓名直接拨打。",
    "english": "各个主题的详细页面是英文的。请拨打 311 并要求中文口译员——"
               "可以说明您需要普通话还是广东话。这项服务免费、任何时间都有，"
               "口译员会全程留在通话中。",
    "needs_h": "您需要哪方面的帮助？",
    "needs_sub": "每一类先列出几家机构，点开可以看到全部。",
    "open_all": "查看全部 {n} 家",
    "vow_h": "我们是谁，以及我们绝不会做的事",
    "vow": "我们是受过训练的学生志愿者。我们帮助您找到纽约处理医疗账单和"
           "保险拒赔的免费项目与专业人士。我们不是医生、律师、福利顾问，"
           "也不是保险专家。我们不看您的账单，不替您填表格，也不告诉您有"
           "资格申请什么。我们把您转介给做这些事的人，而他们免费提供服务。"
           "我们从不收取任何费用。",
    "vow_src": "这段话印在我们发出的每一份材料上，也在每一张服务台前当面说明。",
    "foot_say": "Waypoint 是纽约市的一支学生志愿者队伍。本页所列的项目都不"
                "是我们运营的。我们帮助大家找到它们。",
    "foot_links": ["寻找帮助", "关于 Waypoint", "成为志愿者",
                   "面向合作机构", "隐私与法律声明"],
    "foot_ver": "共 {n} 项资源。最近核对：{when}。项目会有变动——如果这里有"
                "任何不准确的地方，请告诉我们。",
    "langbar_h": "用您的语言获取帮助",
    "english_h": "关于语言",
    "home": 'Waypoint 首页',
    "nav_label": '主导航',
    "skip": "跳到列表",
    "here": "您正在阅读本页",
}

UI["korean"] = {
    "nav": ["도움 찾기", "의료비와 보험 거절", "이용 방법", "학생", "협력 기관"],
    "eyebrow": "Waypoint · 뉴욕시",
    "title_a": "뉴욕시의",
    "title_b": "무료 도움.",
    "lede1": "뉴욕 시민에게 음식, 의료비, 주거, 의료, 법률 문제 등을 도와주는 "
             "{n}곳의 목록입니다. 거의 모두 무료입니다. 대부분은 체류 신분을 "
             "묻지 않습니다.",
    "lede2": "계정을 만들 필요가 없습니다. 저희에게 아무것도 말씀하지 않으셔도 "
             "됩니다. 아래에서 필요한 것을 고르고 직접 전화하십시오.",
    "sos_h": "지금 당장 도움이 필요하시면",
    "sos": ["위험한 상황이거나 누군가 크게 다쳤을 때",
            "스스로가 안전하지 않다고 느끼거나 지금 누군가와 이야기해야 할 때",
            "집에 있는 사람이나 배우자·연인이 해치거나 겁을 줄 때",
            "그 밖의 모든 것. 무료, 24시간, 한국어로"],
    "sos_note": "이 번호들은 모두 무료이며, 바로 이런 일을 위해 훈련받은 "
                "사람이 받습니다. 이름을 밝히지 않고 전화하셔도 됩니다.",
    "english": "각 주제의 상세 페이지는 영어로 되어 있습니다. 311로 전화해 "
               "한국어 통역을 요청하십시오. 무료이고 24시간 이용할 수 있으며, "
               "통역사가 통화 내내 함께합니다.",
    "needs_h": "어떤 도움이 필요하십니까?",
    "needs_sub": "각 항목에 몇 곳이 먼저 보이고, 누르면 전체 목록이 열립니다.",
    "open_all": "{n}곳 모두 보기",
    "vow_h": "저희가 누구인지, 그리고 절대 하지 않는 일",
    "vow": "저희는 교육을 받은 학생 자원봉사자입니다. 뉴욕에서 의료비와 보험 "
           "거절 문제를 다루는 무료 프로그램과 전문가를 찾아 드립니다. 저희는 "
           "의사도, 변호사도, 복지 상담사도, 보험 전문가도 아닙니다. 청구서를 "
           "대신 읽어 드리지 않고, 서류를 대신 작성하지 않으며, 무엇을 받을 수 "
           "있는지 판단해 드리지 않습니다. 그 일을 하는 사람들에게 연결해 "
           "드리고, 그분들은 무료로 해 드립니다. 저희는 어떤 것에도 요금을 "
           "받지 않습니다.",
    "vow_src": "저희가 나눠 드리는 모든 자료에 인쇄되어 있고, 모든 상담 "
               "테이블에서 소리 내어 말씀드리는 내용입니다.",
    "foot_say": "Waypoint는 뉴욕시의 학생 자원봉사 단체입니다. 이 페이지의 "
                "프로그램은 저희가 운영하는 것이 아닙니다. 저희는 사람들이 "
                "그것을 찾도록 돕습니다.",
    "foot_links": ["도움 찾기", "Waypoint 소개", "자원봉사 신청",
                   "기관을 위한 안내", "개인정보 및 법적 고지"],
    "foot_ver": "자료 {n}건. 마지막 확인: {when}. 프로그램은 바뀝니다 — 여기 "
                "잘못된 내용이 있으면 알려 주십시오.",
    "langbar_h": "사용하시는 언어로 도움 받기",
    "english_h": "언어 안내",
    "home": 'Waypoint 홈',
    "nav_label": '기본 메뉴',
    "skip": "목록으로 건너뛰기",
    "here": "지금 이 페이지를 보고 계십니다",
}

UI["bengali"] = {
    "nav": ["সাহায্য খুঁজুন", "বিল ও প্রত্যাখ্যান", "কীভাবে কাজ করে",
            "শিক্ষার্থী", "সংস্থা"],
    "eyebrow": "Waypoint · নিউ ইয়র্ক সিটি",
    "title_a": "নিউ ইয়র্ক সিটিতে",
    "title_b": "বিনামূল্যে সাহায্য।",
    "lede1": "এখানে {n}টি জায়গার তালিকা আছে, যারা নিউ ইয়র্কের মানুষকে খাবার, "
             "ডাক্তারের বিল, বাসস্থান, স্বাস্থ্যসেবা, আইনি সমস্যা এবং আরও অনেক "
             "কিছুতে সাহায্য করে। প্রায় সবই বিনামূল্যে। বেশিরভাগ জায়গা আপনার "
             "অভিবাসন অবস্থা জিজ্ঞেস করে না।",
    "lede2": "কোনও অ্যাকাউন্ট খুলতে হবে না। আমাদের কিছু বলতেও হবে না। নিচে "
             "আপনার যা দরকার তা বেছে নিন, আর নিজেই ফোন করুন।",
    "sos_h": "এখনই সাহায্য দরকার হলে",
    "sos": ["আপনি বিপদে আছেন, বা কেউ গুরুতর আহত হয়েছেন",
            "নিজেকে নিয়ে নিরাপদ বোধ করছেন না, বা এখনই কারও সঙ্গে কথা বলা দরকার",
            "বাড়ির কেউ বা আপনার সঙ্গী আপনাকে আঘাত করছে বা ভয় দেখাচ্ছে",
            "আর যা কিছু। বিনামূল্যে, যেকোনও সময়, আপনার ভাষায়"],
    "sos_note": "এই লাইনগুলো বিনামূল্যে, আর যাঁরা ধরেন তাঁরা ঠিক এই কাজের জন্যই "
                "প্রশিক্ষিত। নাম না বলেও ফোন করতে পারেন।",
    "english": "প্রতিটি বিষয়ের পাতা ইংরেজিতে। 311 নম্বরে ফোন করে বাংলা দোভাষী "
               "চান — এটি বিনামূল্যে, যেকোনও সময়, আর দোভাষী পুরো কথোপকথনে "
               "আপনার সঙ্গে থাকেন।",
    "needs_h": "আপনার কীসে সাহায্য দরকার?",
    "needs_sub": "প্রতিটিতে কয়েকটি জায়গা দেখানো আছে, আর খুললে সব ক’টি পাওয়া যাবে।",
    "open_all": "সবগুলো দেখুন ({n})",
    "vow_h": "আমরা কারা, আর কী আমরা কখনও করব না",
    "vow": "আমরা প্রশিক্ষিত শিক্ষার্থী স্বেচ্ছাসেবক। নিউ ইয়র্কে ডাক্তারের বিল আর "
           "বিমার প্রত্যাখ্যান নিয়ে কাজ করে এমন বিনামূল্যের প্রোগ্রাম ও "
           "পেশাদারদের খুঁজে পেতে আমরা সাহায্য করি। আমরা ডাক্তার নই, আইনজীবী নই, "
           "সুবিধা-পরামর্শদাতা নই, বিমা বিশেষজ্ঞও নই। আমরা আপনার বিল পড়ি না, "
           "আপনার ফর্ম পূরণ করি না, আর আপনি কীসের যোগ্য তা-ও বলি না। যাঁরা এই "
           "কাজ করেন তাঁদের সঙ্গে আমরা আপনাকে যুক্ত করি, আর তাঁরা তা বিনামূল্যে "
           "করেন। আমরা কোনও কিছুর জন্য কখনও টাকা নিই না।",
    "vow_src": "আমরা যা কিছু বিলি করি তার সবেতেই এটি ছাপা থাকে, আর প্রতিটি "
               "টেবিলে মুখে বলেও দেওয়া হয়।",
    "foot_say": "Waypoint নিউ ইয়র্ক সিটির একটি শিক্ষার্থী স্বেচ্ছাসেবক দল। এই "
                "পাতার কোনও প্রোগ্রামই আমরা চালাই না। আমরা মানুষকে সেগুলো খুঁজে "
                "পেতে সাহায্য করি।",
    "foot_links": ["সাহায্য খুঁজুন", "Waypoint সম্পর্কে", "স্বেচ্ছাসেবক হোন",
                   "সংস্থার জন্য", "গোপনীয়তা ও আইনি তথ্য"],
    "foot_ver": "{n}টি তথ্যসূত্র। সর্বশেষ যাচাই: {when}। প্রোগ্রাম বদলায় — এখানে "
                "কিছু ভুল থাকলে আমাদের জানান।",
    "langbar_h": "আপনার ভাষায় সাহায্য নিন",
    "english_h": "ভাষা সম্পর্কে",
    "home": 'Waypoint, প্রথম পাতা',
    "nav_label": 'প্রধান নেভিগেশন',
    "skip": "তালিকায় যান",
    "here": "আপনি এই পাতাটি পড়ছেন",
}

UI["arabic"] = {
    "nav": ["ابحث عن مساعدة", "الفواتير والرفض", "كيف يعمل الأمر",
            "الطلاب", "المؤسسات"],
    "eyebrow": "Waypoint · مدينة نيويورك",
    "title_a": "مساعدة مجانية",
    "title_b": "في مدينة نيويورك.",
    "lede1": "هذه قائمة بـ {n} جهة تساعد سكان نيويورك في الطعام وفواتير "
             "العلاج والسكن والرعاية الصحية والمسائل القانونية وغيرها. جميعها "
             "تقريبًا مجاني، ومعظمها لا يسأل عن وضعك من ناحية الهجرة.",
    "lede2": "لا تحتاج إلى إنشاء حساب، ولا إلى إخبارنا بأي شيء. اختر ما "
             "تحتاجه أدناه واتصل بنفسك.",
    "sos_h": "إذا كنت تحتاج المساعدة الآن",
    "sos": ["أنت في خطر، أو هناك شخص مصاب إصابة بالغة",
            "لا تشعر بالأمان على نفسك، أو تحتاج إلى التحدث مع شخص الآن",
            "شخص في المنزل أو شريكك يؤذيك أو يخيفك",
            "أي شيء آخر. مجاني، في أي وقت، وبلغتك"],
    "sos_note": "هذه الخطوط مجانية، ويرد عليها أشخاص مدرَّبون على هذا تحديدًا. "
                "يمكنك الاتصال دون ذكر اسمك.",
    "english": "صفحات كل موضوع مكتوبة بالإنجليزية. اتصل بالرقم 311 واطلب "
               "مترجمًا للغة العربية — الخدمة مجانية ومتاحة في أي وقت، "
               "والمترجم يبقى معك طوال المكالمة.",
    "needs_h": "في أي شيء تحتاج المساعدة؟",
    "needs_sub": "كل بطاقة تعرض بعض الجهات، وتفتح صفحة تضمها كلها.",
    "open_all": "اعرض الكل ({n})",
    "vow_h": "من نحن، وما الذي لن نفعله أبدًا",
    "vow": "نحن طلاب متطوعون مدرَّبون. نساعدك على إيجاد البرامج المجانية "
           "والمختصين في نيويورك الذين يتعاملون مع فواتير العلاج ورفض شركات "
           "التأمين. نحن لسنا أطباء ولا محامين ولا مستشاري مساعدات ولا خبراء "
           "تأمين. لا نقرأ فواتيرك، ولا نملأ استماراتك، ولا نخبرك بما يحق لك. "
           "نوصلك بمن يقوم بذلك، وهم يقومون به مجانًا. ولا نتقاضى أي مقابل أبدًا.",
    "vow_src": "هذا مطبوع على كل ما نوزعه، ويُقال بصوت مسموع عند كل طاولة.",
    "foot_say": "Waypoint فريق من الطلاب المتطوعين في مدينة نيويورك. نحن لا "
                "ندير أيًا من البرامج المذكورة في هذه الصفحة، بل نساعد الناس "
                "على الوصول إليها.",
    "foot_links": ["ابحث عن مساعدة", "عن Waypoint", "تطوّع معنا",
                   "للمؤسسات", "الخصوصية والإشعارات القانونية"],
    "foot_ver": "{n} مورد. آخر تحقق: {when}. البرامج تتغيّر — إذا كان هنا شيء "
                "غير صحيح فأخبرنا.",
    "langbar_h": "احصل على المساعدة بلغتك",
    "english_h": "عن اللغة",
    "home": 'Waypoint، الصفحة الرئيسية',
    "nav_label": 'التنقل الرئيسي',
    "skip": "انتقل إلى القائمة",
    "here": "أنت تقرأ هذه الصفحة",
}

UI["urdu"] = {
    "nav": ["مدد تلاش کریں", "بل اور انکار", "یہ کیسے کام کرتا ہے",
            "طلبہ", "ادارے"],
    "eyebrow": "Waypoint · نیو یارک سٹی",
    "title_a": "نیو یارک سٹی میں",
    "title_b": "مفت مدد۔",
    "lede1": "یہ {n} جگہوں کی فہرست ہے جو نیو یارک کے لوگوں کی کھانے، علاج کے "
             "بلوں، رہائش، صحت کی دیکھ بھال، قانونی مسائل اور بہت کچھ میں مدد "
             "کرتی ہیں۔ تقریباً سب مفت ہیں۔ زیادہ تر امیگریشن اسٹیٹس کے بارے "
             "میں نہیں پوچھتیں۔",
    "lede2": "کوئی اکاؤنٹ بنانے کی ضرورت نہیں۔ ہمیں کچھ بتانے کی بھی ضرورت "
             "نہیں۔ نیچے سے جو چاہیے وہ منتخب کریں اور خود فون کریں۔",
    "sos_h": "اگر ابھی مدد چاہیے",
    "sos": ["آپ خطرے میں ہیں، یا کوئی شدید زخمی ہے",
            "آپ خود کو محفوظ محسوس نہیں کر رہے، یا ابھی کسی سے بات کرنی ہے",
            "گھر کا کوئی فرد یا آپ کا ساتھی آپ کو تکلیف دے رہا ہے یا ڈرا رہا ہے",
            "اور جو کچھ بھی۔ مفت، کسی بھی وقت، آپ کی زبان میں"],
    "sos_note": "یہ لائنیں مفت ہیں، اور فون اٹھانے والے اسی کام کے لیے تربیت "
                "یافتہ ہیں۔ آپ اپنا نام بتائے بغیر بھی فون کر سکتے ہیں۔",
    "english": "ہر موضوع کے صفحات انگریزی میں ہیں۔ 311 پر فون کریں اور اردو "
               "مترجم مانگیں — یہ مفت ہے، کسی بھی وقت، اور مترجم پوری بات چیت "
               "میں آپ کے ساتھ رہتا ہے۔",
    "needs_h": "آپ کو کس چیز میں مدد چاہیے؟",
    "needs_sub": "ہر کارڈ پر چند جگہیں دکھائی گئی ہیں، اور کھولنے پر سب مل جاتی ہیں۔",
    "open_all": "سب دیکھیں ({n})",
    "vow_h": "ہم کون ہیں، اور کیا ہم کبھی نہیں کریں گے",
    "vow": "ہم تربیت یافتہ طالب علم رضاکار ہیں۔ ہم آپ کو نیو یارک کے وہ مفت "
           "پروگرام اور ماہرین تلاش کرنے میں مدد دیتے ہیں جو علاج کے بلوں اور "
           "بیمہ کے انکار سے نمٹتے ہیں۔ ہم ڈاکٹر، وکیل، فوائد کے مشیر یا بیمہ "
           "کے ماہر نہیں ہیں۔ ہم آپ کے بل نہیں پڑھتے، آپ کے فارم نہیں بھرتے، "
           "اور یہ نہیں بتاتے کہ آپ کس چیز کے اہل ہیں۔ ہم آپ کو ان لوگوں سے "
           "ملاتے ہیں جو یہ کام کرتے ہیں، اور وہ یہ مفت کرتے ہیں۔ ہم کسی چیز "
           "کے پیسے کبھی نہیں لیتے۔",
    "vow_src": "یہ ہر اُس چیز پر چھپا ہوتا ہے جو ہم تقسیم کرتے ہیں، اور ہر میز "
               "پر بول کر بھی بتایا جاتا ہے۔",
    "foot_say": "Waypoint نیو یارک سٹی کے طالب علم رضاکاروں کا ایک گروپ ہے۔ اس "
                "صفحے کا کوئی پروگرام ہم نہیں چلاتے۔ ہم لوگوں کو انہیں تلاش "
                "کرنے میں مدد دیتے ہیں۔",
    "foot_links": ["مدد تلاش کریں", "Waypoint کے بارے میں", "رضاکار بنیں",
                   "اداروں کے لیے", "پرائیویسی اور قانونی معلومات"],
    "foot_ver": "{n} وسائل۔ آخری جانچ: {when}۔ پروگرام بدلتے رہتے ہیں — اگر "
                "یہاں کچھ غلط ہو تو ہمیں بتائیں۔",
    "langbar_h": "اپنی زبان میں مدد حاصل کریں",
    "english_h": "زبان کے بارے میں",
    "home": 'Waypoint، مرکزی صفحہ',
    "nav_label": 'مرکزی نیویگیشن',
    "skip": "فہرست پر جائیں",
    "here": "آپ یہ صفحہ پڑھ رہے ہیں",
}


# The line under each of the seventeen headings. The heading itself is already
# in build_help.LANGUAGES[...]["needs"] — this is the sentence that tells you
# what is actually behind it.
BLURBS = {}

BLURBS["spanish"] = {
    "safety": "Alguien de su casa, o su pareja, le hace daño o le amenaza.",
    "crisis": "No se siente seguro consigo mismo, está desbordado, o tiene problemas con el alcohol o las drogas.",
    "food": "Despensas, comidas calientes y ayuda para inscribirse en cupones de alimentos (SNAP).",
    "housing": "Un lugar donde dormir esta noche, ayuda con el desalojo y vivienda asequible.",
    "bills": "Los expertos gratuitos que se ocupan de facturas de hospital, rechazos del seguro y el costo de los medicamentos.",
    "doctor": "Clínicas que le atienden tenga o no seguro o papeles.",
    "legal": "Ayuda legal gratuita: vivienda, inmigración, beneficios y más.",
    "money": "Ayuda en efectivo, la factura de la calefacción, declaración de impuestos gratis y beneficios.",
    "family": "Cuidado de niños, centros para jóvenes y alojamiento para jóvenes solos.",
    "senior": "Comidas, centros y ayuda para los neoyorquinos mayores.",
    "clothes": "Ropa gratis, abrigos de invierno, pañales y cosas para niños.",
    "work": "Formación laboral, trabajo pagado para jóvenes y clases de inglés.",
    "getting-there": "MetroCard a mitad de precio, viajes a citas médicas y Access-A-Ride.",
    "veterans": "Atención médica y servicios para quienes sirvieron en las fuerzas armadas.",
    "disability": "Beneficios, transporte, vivienda accesible y qué hacer si le dicen que no.",
    "record": "Trabajo, vivienda y ayuda legal después de la cárcel o la prisión.",
    "start": "Un solo teléfono, o una sola página, que le lleva a todo lo demás.",
}

BLURBS["french"] = {
    "safety": "Quelqu’un chez vous, ou votre partenaire, vous fait du mal ou vous menace.",
    "crisis": "Vous ne vous sentez pas en sécurité avec vous-même, vous êtes dépassé, ou vous avez un problème d’alcool ou de drogue.",
    "food": "Distributions alimentaires, repas chauds et aide pour s’inscrire aux coupons alimentaires (SNAP).",
    "housing": "Un lit ce soir, de l’aide contre l’expulsion et des logements abordables.",
    "bills": "Les spécialistes gratuits qui s’occupent des factures d’hôpital, des refus d’assurance et du prix des médicaments.",
    "doctor": "Des cliniques qui vous reçoivent, que vous ayez ou non une assurance ou des papiers.",
    "legal": "Aide juridique gratuite : logement, immigration, prestations et plus.",
    "money": "Aide en espèces, facture de chauffage, déclaration d’impôts gratuite et prestations.",
    "family": "Garde d’enfants, centres d’accueil pour jeunes et hébergement pour jeunes seuls.",
    "senior": "Repas, centres et aide pour les New-Yorkais âgés.",
    "clothes": "Vêtements gratuits, manteaux d’hiver, couches et affaires pour enfants.",
    "work": "Formation professionnelle, emplois rémunérés pour les jeunes et cours d’anglais.",
    "getting-there": "MetroCard à moitié prix, trajets vers les rendez-vous médicaux et Access-A-Ride.",
    "veterans": "Soins et services pour ceux qui ont servi dans l’armée.",
    "disability": "Prestations, déplacements, logement accessible, et que faire en cas de refus.",
    "record": "Emploi, logement et aide juridique après la prison.",
    "start": "Un seul numéro, ou un seul site, qui mène à tout le reste.",
}

BLURBS["polish"] = {
    "safety": "Ktoś w domu albo partner rani cię lub ci grozi.",
    "crisis": "Brak poczucia bezpieczeństwa ze sobą, przytłoczenie albo problem z alkoholem lub narkotykami.",
    "food": "Punkty z żywnością, ciepłe posiłki i pomoc w zapisaniu się na bony żywnościowe (SNAP).",
    "housing": "Nocleg na dziś, pomoc przy eksmisji i tanie mieszkania.",
    "bills": "Bezpłatni specjaliści od rachunków szpitalnych, odmów ubezpieczenia i kosztów leków.",
    "doctor": "Przychodnie, które przyjmą niezależnie od ubezpieczenia i dokumentów.",
    "legal": "Bezpłatna pomoc prawna: mieszkanie, imigracja, świadczenia i więcej.",
    "money": "Zasiłek pieniężny, rachunek za ogrzewanie, bezpłatne rozliczenie podatku i świadczenia.",
    "family": "Opieka nad dziećmi, świetlice dla młodzieży i schronienie dla samotnych młodych osób.",
    "senior": "Posiłki, ośrodki i pomoc dla starszych mieszkańców Nowego Jorku.",
    "clothes": "Bezpłatne ubrania, zimowe kurtki, pieluchy i rzeczy dla dzieci.",
    "work": "Szkolenia zawodowe, płatna praca dla młodzieży i kursy angielskiego.",
    "getting-there": "MetroCard za pół ceny, dojazd na wizyty lekarskie i Access-A-Ride.",
    "veterans": "Opieka zdrowotna i usługi dla osób, które służyły w wojsku.",
    "disability": "Świadczenia, poruszanie się, dostępne mieszkania i co zrobić po odmowie.",
    "record": "Praca, mieszkanie i pomoc prawna po wyjściu z więzienia.",
    "start": "Jeden numer albo jedna strona, które prowadzą do całej reszty.",
}

BLURBS["haitian-creole"] = {
    "safety": "Yon moun lakay ou, oswa patnè ou, ap fè ou mal oswa ap menase ou.",
    "crisis": "Ou pa santi ou an sekirite ak tèt ou, ou depase, oswa ou gen pwoblèm ak alkòl oswa dwòg.",
    "food": "Depo manje, manje cho, ak èd pou enskri nan koupon manje (SNAP).",
    "housing": "Kote pou dòmi aswè a, èd kont degèpisman, ak lojman ki pa chè.",
    "bills": "Espesyalis gratis ki okipe bòdwo lopital, refi asirans, ak pri medikaman.",
    "doctor": "Klinik ki resevwa ou kit ou gen asirans oswa papye, kit ou pa genyen.",
    "legal": "Èd legal gratis: lojman, imigrasyon, benefis, ak plis ankò.",
    "money": "Èd an lajan kach, bòdwo chofaj, deklarasyon taks gratis, ak benefis.",
    "family": "Gadri, sant pou jèn moun, ak kote pou jèn ki poukont yo rete.",
    "senior": "Manje, sant, ak èd pou granmoun aje nan Nouyòk.",
    "clothes": "Rad gratis, manto pou sezon fredi, kouchèt, ak bagay pou timoun.",
    "work": "Fòmasyon travay, travay peye pou jèn moun, ak kou anglè.",
    "getting-there": "MetroCard a mwatye pri, transpò pou randevou doktè, ak Access-A-Ride.",
    "veterans": "Swen sante ak sèvis pou moun ki te sèvi nan lame.",
    "disability": "Benefis, deplasman, lojman aksesib, ak sa pou fè si yo di ou non.",
    "record": "Travay, lojman, ak èd legal apre prizon.",
    "start": "Yon sèl nimewo telefòn, oswa yon sèl sit, ki mennen ou nan tout rès la.",
}

BLURBS["russian"] = {
    "safety": "Кто-то дома или партнёр причиняет боль или угрожает.",
    "crisis": "Небезопасно наедине с собой, всё навалилось, или проблемы с алкоголем либо наркотиками.",
    "food": "Продуктовые пункты, горячая еда и помощь с оформлением продуктовых талонов (SNAP).",
    "housing": "Койка на сегодня, помощь при выселении и доступное жильё.",
    "bills": "Бесплатные специалисты по больничным счетам, отказам страховой и стоимости лекарств.",
    "doctor": "Клиники, которые примут вне зависимости от страховки и документов.",
    "legal": "Бесплатная юридическая помощь: жильё, иммиграция, пособия и не только.",
    "money": "Денежная помощь, счёт за отопление, бесплатная подача налоговой декларации и пособия.",
    "family": "Детский сад, центры для подростков и жильё для молодых людей без семьи.",
    "senior": "Питание, центры и помощь для пожилых жителей Нью-Йорка.",
    "clothes": "Бесплатная одежда, зимние куртки, подгузники и вещи для детей.",
    "work": "Обучение профессии, оплачиваемая работа для молодёжи и курсы английского.",
    "getting-there": "MetroCard за полцены, поездки на приём к врачу и Access-A-Ride.",
    "veterans": "Медицинская помощь и услуги для тех, кто служил в армии.",
    "disability": "Пособия, передвижение по городу, доступное жильё и что делать при отказе.",
    "record": "Работа, жильё и юридическая помощь после тюрьмы.",
    "start": "Один номер телефона или один сайт, откуда можно дойти до всего остального.",
}

BLURBS["chinese"] = {
    "safety": "家里的人或伴侣正在伤害您、威胁您。",
    "crisis": "担心自己的安全、感到承受不住，或者有酒精、药物方面的困扰。",
    "food": "食物发放点、热餐，以及申请食品券（SNAP）的协助。",
    "housing": "今晚的住处、防止被驱逐的帮助，以及可负担住房。",
    "bills": "处理医院账单、保险拒赔和药费的免费专业人士。",
    "doctor": "无论有没有保险或身份证件都接诊的诊所。",
    "legal": "免费法律帮助：住房、移民、福利等。",
    "money": "现金补助、取暖费、免费报税，以及各项福利。",
    "family": "托儿服务、青少年活动中心，以及给独自生活的青少年的住处。",
    "senior": "为纽约长者提供的餐食、活动中心和各项帮助。",
    "clothes": "免费衣物、冬季外套、尿布和儿童用品。",
    "work": "职业培训、青少年带薪工作，以及英语课程。",
    "getting-there": "半价 MetroCard、就医接送，以及 Access-A-Ride。",
    "veterans": "为服过兵役的人提供的医疗和服务。",
    "disability": "福利、出行、无障碍住房，以及被拒绝时该怎么办。",
    "record": "出狱之后的工作、住房和法律帮助。",
    "start": "一个电话号码，或一个网站，帮您找到其余所有资源。",
}

BLURBS["korean"] = {
    "safety": "집에 있는 사람이나 배우자·연인이 해치거나 위협하는 경우.",
    "crisis": "스스로가 안전하지 않다고 느끼거나, 감당하기 어렵거나, 술·약물 문제가 있는 경우.",
    "food": "식품 배급소, 따뜻한 식사, 푸드스탬프(SNAP) 신청 도움.",
    "housing": "오늘 밤 묵을 곳, 퇴거를 막는 도움, 그리고 저렴한 주택.",
    "bills": "병원비, 보험 거절, 약값을 다루는 무료 전문가들.",
    "doctor": "보험이나 신분증이 있든 없든 진료해 주는 병원.",
    "legal": "무료 법률 지원 — 주거, 이민, 복지 혜택 등.",
    "money": "현금 지원, 난방비, 무료 세금 신고, 그리고 각종 복지 혜택.",
    "family": "보육, 청소년 센터, 혼자 지내는 청소년을 위한 쉼터.",
    "senior": "뉴욕의 어르신을 위한 식사, 센터, 각종 지원.",
    "clothes": "무료 의류, 겨울 외투, 기저귀, 아이 용품.",
    "work": "직업 훈련, 청소년 유급 일자리, 영어 수업.",
    "getting-there": "반값 메트로카드, 병원 진료 교통편, Access-A-Ride.",
    "veterans": "군 복무를 한 분들을 위한 의료와 서비스.",
    "disability": "복지 혜택, 이동, 장애인 접근 가능 주택, 그리고 거절당했을 때.",
    "record": "출소 후의 일자리, 주거, 법률 지원.",
    "start": "나머지 전부로 이어지는 전화번호 하나, 또는 웹사이트 하나.",
}

BLURBS["bengali"] = {
    "safety": "বাড়ির কেউ, বা আপনার সঙ্গী, আঘাত করছে বা ভয় দেখাচ্ছে।",
    "crisis": "নিজেকে নিয়ে নিরাপদ বোধ করছেন না, সব কিছু অসহ্য লাগছে, বা মদ কিংবা মাদকের সমস্যা আছে।",
    "food": "খাবার বিতরণ কেন্দ্র, গরম খাবার, আর ফুড স্ট্যাম্প (SNAP)-এ নাম লেখাতে সাহায্য।",
    "housing": "আজ রাতে থাকার জায়গা, উচ্ছেদ ঠেকাতে সাহায্য, আর সাশ্রয়ী বাসস্থান।",
    "bills": "হাসপাতালের বিল, বিমার প্রত্যাখ্যান আর ওষুধের খরচ নিয়ে কাজ করেন এমন বিনামূল্যের বিশেষজ্ঞরা।",
    "doctor": "বিমা বা কাগজপত্র থাকুক বা না থাকুক, যেসব ক্লিনিক দেখে।",
    "legal": "বিনামূল্যে আইনি সহায়তা — বাসস্থান, অভিবাসন, সরকারি সুবিধা এবং আরও।",
    "money": "নগদ সহায়তা, হিটিং বিল, বিনামূল্যে ট্যাক্স ফাইলিং, আর নানা সুবিধা।",
    "family": "শিশু দেখাশোনা, তরুণদের কেন্দ্র, আর একা থাকা তরুণদের জন্য আশ্রয়।",
    "senior": "নিউ ইয়র্কের প্রবীণদের জন্য খাবার, কেন্দ্র আর সহায়তা।",
    "clothes": "বিনামূল্যে জামাকাপড়, শীতের কোট, ডায়াপার আর শিশুদের জিনিস।",
    "work": "কাজের প্রশিক্ষণ, তরুণদের জন্য বেতনের কাজ, আর ইংরেজি ক্লাস।",
    "getting-there": "অর্ধেক দামে MetroCard, ডাক্তারের অ্যাপয়েন্টমেন্টে যাতায়াত, আর Access-A-Ride।",
    "veterans": "যাঁরা সেনাবাহিনীতে ছিলেন তাঁদের জন্য স্বাস্থ্যসেবা ও পরিষেবা।",
    "disability": "সুবিধা, চলাফেরা, প্রবেশযোগ্য বাসস্থান, আর প্রত্যাখ্যাত হলে কী করবেন।",
    "record": "জেল থেকে ফেরার পর কাজ, বাসস্থান আর আইনি সহায়তা।",
    "start": "একটি ফোন নম্বর, বা একটি ওয়েবসাইট, যা বাকি সব কিছুতে পৌঁছে দেয়।",
}

BLURBS["arabic"] = {
    "safety": "شخص في المنزل، أو شريكك، يؤذيك أو يهدّدك.",
    "crisis": "لا تشعر بالأمان على نفسك، أو الأمور فوق طاقتك، أو لديك مشكلة مع الكحول أو المخدرات.",
    "food": "بنوك طعام ووجبات ساخنة ومساعدة في التسجيل لكوبونات الطعام (SNAP).",
    "housing": "مكان للمبيت الليلة، ومساعدة ضد الإخلاء، وسكن بأسعار معقولة.",
    "bills": "مختصون مجانًا يتعاملون مع فواتير المستشفى ورفض التأمين وتكاليف الأدوية.",
    "doctor": "عيادات تستقبلك سواء كان لديك تأمين أو أوراق أو لم يكن.",
    "legal": "مساعدة قانونية مجانية: السكن والهجرة والمساعدات وغيرها.",
    "money": "مساعدة نقدية، وفاتورة التدفئة، وتقديم الضرائب مجانًا، والمساعدات.",
    "family": "رعاية الأطفال، ومراكز للشباب، ومأوى للشباب الذين بلا عائلة.",
    "senior": "وجبات ومراكز ومساعدة لكبار السن في نيويورك.",
    "clothes": "ملابس مجانية ومعاطف شتوية وحفاضات ومستلزمات الأطفال.",
    "work": "تدريب مهني، وعمل مدفوع للشباب، ودروس في الإنجليزية.",
    "getting-there": "بطاقة MetroCard بنصف السعر، وتوصيل إلى مواعيد العلاج، وAccess-A-Ride.",
    "veterans": "رعاية صحية وخدمات لمن خدموا في الجيش.",
    "disability": "المساعدات، والتنقل، والسكن الميسَّر، وماذا تفعل إذا رُفض طلبك.",
    "record": "عمل وسكن ومساعدة قانونية بعد السجن.",
    "start": "رقم هاتف واحد، أو موقع واحد، يدلّك على كل ما عداه.",
}

BLURBS["urdu"] = {
    "safety": "گھر کا کوئی فرد، یا آپ کا ساتھی، تکلیف دے رہا ہے یا دھمکا رہا ہے۔",
    "crisis": "خود کو محفوظ محسوس نہ کرنا، سب کچھ بس سے باہر لگنا، یا شراب یا منشیات کا مسئلہ۔",
    "food": "کھانے کے مراکز، گرم کھانا، اور فوڈ اسٹیمپ (SNAP) میں نام لکھوانے میں مدد۔",
    "housing": "آج رات رہنے کی جگہ، بے دخلی کے خلاف مدد، اور سستی رہائش۔",
    "bills": "ہسپتال کے بلوں، بیمہ کے انکار اور دواؤں کے خرچ سے نمٹنے والے مفت ماہرین۔",
    "doctor": "ایسے کلینک جو بیمہ یا کاغذات ہوں یا نہ ہوں، دیکھتے ہیں۔",
    "legal": "مفت قانونی مدد — رہائش، امیگریشن، فوائد اور بہت کچھ۔",
    "money": "نقد امداد، ہیٹنگ کا بل، مفت ٹیکس فائلنگ، اور مختلف فوائد۔",
    "family": "بچوں کی دیکھ بھال، نوجوانوں کے مراکز، اور اکیلے نوجوانوں کے لیے رہائش۔",
    "senior": "نیو یارک کے بزرگوں کے لیے کھانا، مراکز اور مدد۔",
    "clothes": "مفت کپڑے، سردی کے کوٹ، ڈائپر اور بچوں کا سامان۔",
    "work": "کام کی تربیت، نوجوانوں کے لیے تنخواہ والا کام، اور انگریزی کی کلاسیں۔",
    "getting-there": "آدھی قیمت پر MetroCard، ڈاکٹر کے اپائنٹمنٹ تک آمد و رفت، اور Access-A-Ride۔",
    "veterans": "فوج میں خدمات انجام دینے والوں کے لیے صحت کی دیکھ بھال اور سہولتیں۔",
    "disability": "فوائد، آمد و رفت، قابلِ رسائی رہائش، اور انکار کی صورت میں کیا کریں۔",
    "record": "جیل کے بعد کام، رہائش اور قانونی مدد۔",
    "start": "ایک فون نمبر، یا ایک ویب سائٹ، جو باقی سب تک پہنچا دے۔",
}


# Month names, and how a span of them reads. The footer said "Last checked
# June-August 2026" on every one of the ten pages, in English, under a
# sentence in Bengali. A date is the one thing on that line a reader checks.
MONTHS = {
    "spanish": ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'],
    "french": ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre'],
    "polish": ['styczeń', 'luty', 'marzec', 'kwiecień', 'maj', 'czerwiec', 'lipiec', 'sierpień', 'wrzesień', 'październik', 'listopad', 'grudzień'],
    "haitian-creole": ['janvye', 'fevriye', 'mas', 'avril', 'me', 'jen', 'jiyè', 'out', 'septanm', 'oktòb', 'novanm', 'desanm'],
    "russian": ['январь', 'февраль', 'март', 'апрель', 'май', 'июнь', 'июль', 'август', 'сентябрь', 'октябрь', 'ноябрь', 'декабрь'],
    "chinese": ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'],
    "korean": ['1월', '2월', '3월', '4월', '5월', '6월', '7월', '8월', '9월', '10월', '11월', '12월'],
    "bengali": ['জানুয়ারি', 'ফেব্রুয়ারি', 'মার্চ', 'এপ্রিল', 'মে', 'জুন', 'জুলাই', 'আগস্ট', 'সেপ্টেম্বর', 'অক্টোবর', 'নভেম্বর', 'ডিসেম্বর'],
    "arabic": ['يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو', 'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر'],
    "urdu": ['جنوری', 'فروری', 'مارچ', 'اپریل', 'مئی', 'جون', 'جولائی', 'اگست', 'ستمبر', 'اکتوبر', 'نومبر', 'دسمبر'],
}

# ("one month", "a span") — Chinese and Korean put the year first.
DATE_SPAN = {
    "spanish": ('{a} de {y}', '{a}–{b} de {y}'),
    "french": ('{a} {y}', 'de {a} à {b} {y}'),
    "polish": ('{a} {y}', '{a}–{b} {y}'),
    "haitian-creole": ('{a} {y}', '{a}–{b} {y}'),
    "russian": ('{a} {y}', '{a}–{b} {y}'),
    "chinese": ('{y}年{a}', '{y}年{a}–{b}'),
    "korean": ('{y}년 {a}', '{y}년 {a}–{b}'),
    "bengali": ('{a} {y}', '{a}–{b} {y}'),
    "arabic": ('{a} {y}', '{a}–{b} {y}'),
    "urdu": ('{a} {y}', '{a}–{b} {y}'),
}

# The masthead title is two halves, roman then gold. Chinese sets them with no
# space between; everything else takes one.
TITLE_JOIN = {"chinese": ""}
