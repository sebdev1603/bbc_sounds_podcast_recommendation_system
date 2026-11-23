"""English and Welsh (Cymraeg) UI translation helpers for BBC Sounds."""
import re

CURRENT_LANGUAGE = "en"

TRANSLATIONS_CY = {
    # Navigation bar & common controls
    "HOME": "HAFAN",
    "GENRES": "GENRES",
    "FOR YOU": "I CHI",
    "FAVOURITES": "FFEFRYNNAU",
    "HISTORY": "HANES",
    "RATINGS": "SGORIAU",
    "REPORT": "ADRODDIAD",
    "SETTINGS": "GOSODIADAU",
    "PROFILE": "PROFFIL",
    "Sign out": "Allgofnodi",
    "Search programmes...": "Chwilio rhaglenni...",
    "‹ Previous": "‹ Blaenorol",
    "Next ›": "Nesaf ›",
    "Details": "Manylion",
    "View details": "Gweld manylion",
    "Remove": "Tynnu",
    "Dismiss": "Cau",
    "Cancel": "Canslo",
    "Clear": "Clirio",
    "▶  Play": "▶  Chwarae",
    "▶  Listen": "▶  Gwrando",
    "▶  Listen now": "▶  Gwrando nawr",
    "▶  Listen again": "▶  Gwrando eto",
    "No more results": "Dim mwy o ganlyniadau",
    "No programmes to show yet": "Dim rhaglenni i'w dangos eto",
    "Try another search, or explore all programmes.": "Rhowch gynnig ar chwiliad arall, neu archwiliwch yr holl raglenni.",

    # Home page
    "Good to have you back!": "Braf eich cael yn ôl!",
    "Settle in and find something worth listening to.": "Ymlaciwch a dewch o hyd i rywbeth werth gwrando arno.",
    "programmes in your history": "o raglenni yn eich hanes",
    "favourites saved": "o ffefrynnau wedi'u cadw",
    "ratings given": "o sgoriau wedi'u rhoi",
    "YOUR LISTENING, SUMMARISED": "EICH GWRANDO, WEDI'I GRYNHOI",
    "See your plays, most-listened programme and average rating.": "Gweld eich gwrandawiadau, eich hoff raglen a'ch sgôr gyfartalog.",
    "Generate listening report": "Creu adroddiad gwrando",
    "Find your next favourite listen": "Dewch o hyd i'ch hoff raglen nesaf",
    "Search thousands of programmes and explore by genre.": "Chwiliwch filoedd o raglenni ac archwiliwch yn ôl genre.",
    "Explore programmes  →": "Archwilio rhaglenni  →",
    "Explore programmes": "Archwilio rhaglenni",
    "Made for you": "Wedi'i wneud i chi",
    "A match for your favourite genres and episode length.": "Yn cyfateb i'ch hoff genres a hyd penodau.",
    "See all": "Gweld y cyfan",
    "Recently played": "Wedi chwarae'n ddiweddar",
    "Pick up right where you left off.": "Parhewch lle gwnaethoch chi adael.",
    "Listening history": "Hanes gwrando",
    "Complete your survey": "Cwblhewch eich arolwg",
    "Tell us your favourite genres and episode length for tailored picks.": "Dywedwch wrthym eich hoff genres a hyd penodau am argymhellion personol.",
    "Take the survey": "Cymryd yr arolwg",

    # Genres & Search page
    "Browse genres": "Pori genres",
    "Choose a genre below, or use the search bar above.": "Dewiswch genre isod, neu defnyddiwch y bar chwilio uchod.",
    "All genres": "Pob genre",
    "Select a genre to see every matching programme.": "Dewiswch genre i weld pob rhaglen sy'n cyfateb.",
    "BROWSE PROGRAMMES  →": "PORI RHAGLENNI  →",
    "Programmes": "Rhaglenni",
    "NEWS": "NEWYDDION",
    "TRAVEL": "TEITHIO",
    "HISTORY": "HANES",
    "COMEDY": "COMEDI",
    "TRUE CRIME": "TROSEDD WIR",
    "TECHNOLOGY": "TECHNOLEG",
    "SCIENCE": "GWYDDONIAETH",
    "BUSINESS": "BUSNES",
    "GAMING": "GEMAU",
    "ENTERTAINMENT": "ADLONIANT",
    "SPORT": "CHWARAEON",
    "HEALTH": "IECHYD",
    "News": "Newyddion",
    "Travel": "Teithio",
    "History": "Hanes",
    "Comedy": "Comedi",
    "True Crime": "Trosedd Wir",
    "Technology": "Technoleg",
    "Science": "Gwyddoniaeth",
    "Business": "Busnes",
    "Gaming": "Gemau",
    "Entertainment": "Adloniant",
    "Sport": "Chwaraeon",
    "Health": "Iechyd",
    "Headlines, investigations and current affairs": "Penawdau, ymchwiliadau a materion cyfoes",
    "Journeys, places and stories from around the world": "Teithiau, lleoedd a straeon o bob cwr o'r byd",
    "People and events that shaped our world": "Pobl a digwyddiadau a luniodd ein byd",
    "Stand-up, panel shows and funny conversations": "Comedi stand-yp, sioeau panel a sgyrsiau doniol",
    "Real cases, mysteries and investigations": "Achosion go iawn, dirgelion ac ymchwiliadau",
    "Digital culture, inventions and the future": "Diwylliant digidol, dyfeisiadau a'r dyfodol",
    "Discoveries, nature and how things work": "Darganfyddiadau, natur a sut mae pethau'n gweithio",
    "Money, markets, careers and entrepreneurship": "Arian, marchnadoedd, gyrfaoedd ac entrepreneuriaeth",
    "Games, creators and player culture": "Gemau, crewyr a diwylliant chwaraewyr",
    "Film, television, music and celebrity stories": "Ffilm, teledu, cerddoriaeth a straeon enwogion",
    "Matches, athletes and expert sporting analysis": "Gemau, athletwyr a dadansoddiad chwaraeon arbenigol",
    "Wellbeing, medicine and healthier living": "Llesiant, meddygaeth a byw'n iachach",

    # For you / Favourites / History / Ratings / Report
    "Recommended for you": "Argymhellion i chi",
    "Picked from your favourite genres and preferred episode length.": "Wedi'u dewis o'ch hoff genres a'ch hyd penodau.",
    "No recommendations yet": "Dim argymhellion eto",
    "Complete your survey so we can tailor recommendations to your taste.": "Cwblhewch eich arolwg fel y gallwn deilwra argymhellion i'ch chwaeth.",
    "Update preferences": "Diweddaru dewisiadau",
    "Your favourites": "Eich ffefrynnau",
    "Programmes you have saved for quick listening.": "Rhaglenni rydych chi wedi'u cadw ar gyfer gwrando cyflym.",
    "No favourites saved yet": "Dim ffefrynnau wedi'u cadw eto",
    "Open any programme and select Save to favourites to build your list.": "Agorwch unrhyw raglen a dewiswch Cadw i ffefrynnau i adeiladu eich rhestr.",
    "Your listening history": "Eich hanes gwrando",
    "Every programme you have played, newest first.": "Pob rhaglen rydych chi wedi'i chwarae, y diweddaraf yn gyntaf.",
    "Clear history": "Clirio hanes",
    "No listening history yet": "Dim hanes gwrando eto",
    "Play a programme and it will appear here automatically.": "Chwaraewch raglen a bydd yn ymddangos yma'n awtomatig.",
    "Podcasts you rated": "Podlediadau rydych chi wedi'u graddio",
    "Every programme you have scored is collected here.": "Mae pob rhaglen rydych chi wedi'i graddio wedi'i chasglu yma.",
    "No ratings yet": "Dim sgoriau eto",
    "Listen to a programme, then add a rating from its details page.": "Gwrandewch ar raglen, yna ychwanegwch sgôr o'i thudalen fanylion.",
    "ratings in your library": "o sgoriau yn eich llyfrgell",
    "Select a programme to update or remove its score.": "Dewiswch raglen i ddiweddaru neu dynnu ei sgôr.",
    "Your rating": "Eich sgôr",
    "Your rating:": "Eich sgôr:",
    "Change rating": "Newid sgôr",
    "Listening report": "Adroddiad gwrando",
    "A snapshot of your plays, top show, and ratings.": "Cipolwg ar eich gwrandawiadau, eich prif sioe a'ch sgoriau.",
    "total plays": "cyfanswm gwrandawiadau",
    "unique programmes": "rhaglenni unigryw",
    "average rating given": "sgôr gyfartalog a roddwyd",
    "MOST PLAYED": "A CHWARAEWYD FWYAF",
    "No listening data yet": "Dim data gwrando eto",
    "Play a programme to start your personal report.": "Chwaraewch raglen i ddechrau eich adroddiad personol.",
    "Your rated programmes": "Eich rhaglenni wedi'u graddio",

    # Profile & Settings page
    "Profile & survey": "Proffil ac arolwg",
    "Update your preferences whenever your listening changes.": "Diweddarwch eich dewisiadau pryd bynnag mae eich gwrando'n newid.",
    "YOUR PROFILE": "EICH PROFFIL",
    "BBC Sounds listener": "Gwrandäwr BBC Sounds",
    "Choose your name...": "Dewiswch eich enw...",
    "Save name": "Cadw enw",
    "Name cleared.": "Enw wedi'i glirio.",
    "Listening preferences": "Dewisiadau gwrando",
    "Survey status: complete": "Statws yr arolwg: wedi'i gwblhau",
    "Survey status: not completed": "Statws yr arolwg: heb ei gwblhau",
    "FAVOURITE GENRES": "HOFF GENRES",
    "PREFERRED EPISODE LENGTH": "HYD PENODAU A DDEWISWYD",
    "None selected": "Dim wedi'i ddewis",
    "Not selected": "Heb ei ddewis",
    "Short": "Byr",
    "Medium": "Canolig",
    "Long": "Hir",
    "Edit survey answers": "Golygu atebion yr arolwg",
    "Reset survey": "Ailosod yr arolwg",
    "Accessibility settings": "Gosodiadau hygyrchedd",
    "Adjust text size, language, and switch between Dark, Light, and High contrast themes.": "Addaswch faint y testun, yr iaith, a newidiwch rhwng themâu Tywyll, Golau a Chyferbyniad Uchel.",
    "Adjust text size and switch between Dark, Light, and High contrast themes.": "Addaswch faint y testun, yr iaith, a newidiwch rhwng themâu Tywyll, Golau a Chyferbyniad Uchel.",
    "TEXT SIZE": "MAINT TESTUN",
    "APPEARANCE THEME": "THEMA YMDDANGOSIAD",
    "LANGUAGE": "IAITH",
    "Dark  ·  Default": "Tywyll  ·  Rhagosodedig",
    "Dark": "Tywyll",
    "Light": "Golau",
    "High contrast": "Cyferbyniad uchel",
    "English": "Saesneg (English)",
    "Cymraeg (Welsh)": "Cymraeg",
    "English  ·  Default": "Saesneg  ·  Rhagosodedig",
    "Cymraeg  ·  Welsh": "Cymraeg",
    "A−  Smaller": "A−  Llai",
    "A+  Larger": "A+  Mwy",
    "ANIMATIONS": "ANIMEIDDIADAU",
    "Smooth  ·  Default": "Llyfn  ·  Rhagosodedig",
    "Reduced motion  ·  Faster on older devices": "Llai o symudiad  ·  Cyflymach ar ddyfeisiau hŷn",
    "Smooth": "Llyfn",
    "Reduced motion": "Llai o symudiad",
    "Reset accessibility settings": "Ailosod gosodiadau hygyrchedd",

    # Q&A section
    "Q&A": "C&A",
    "Select a question below to see how BBC Sounds features work.": "Dewiswch gwestiwn isod i weld sut mae nodweddion BBC Sounds yn gweithio.",
    "How are my recommendations chosen?": "Sut mae fy argymhellion yn cael eu dewis?",
    "Recommendations on the For you tab match your saved favourite genres and preferred episode length (Short, Medium, or Long), weighted toward higher-rated programmes.": "Mae argymhellion ar y tab I chi yn cyfateb i'ch hoff genres a'ch hyd penodau (Byr, Canolig, neu Hir), wedi'u pwysoli tuag at raglenni â sgôr uwch.",
    "How do I rate a programme?": "Sut ydw i'n graddio rhaglen?",
    "Open any podcast by clicking its picture or Details button, press Listen now at least once, and then click Rate this programme to choose a 1 to 5 star score.": "Agorwch unrhyw bodlediad drwy glicio ei lun neu'r botwm Manylion, pwyswch Gwrando nawr o leiaf unwaith, ac yna cliciwch Graddio'r rhaglen hon i ddewis sgôr rhwng 1 a 5 seren.",
    "Why does it say playback is simulated?": "Pam mae'n dweud bod y chwarae wedi'i efelychu?",
    "This desktop prototype simulates audio playback so you can explore recommendations, track your listening history, and rate programmes without streaming live audio.": "Mae'r prototeip bwrdd gwaith hwn yn efelychu chwarae sain fel y gallwch archwilio argymhellion, tracio eich hanes gwrando, a graddio rhaglenni heb ffrydio sain fyw.",
    "How do I save or remove favourites?": "Sut ydw i'n cadw neu dynnu ffefrynnau?",
    "Click any podcast picture to open its details page, then click Save to favourites. Saved shows appear in the Favourites tab and can be removed at any time.": "Cliciwch unrhyw lun podlediad i agor ei dudalen fanylion, yna cliciwch Cadw i ffefrynnau. Mae sioeau wedi'u cadw yn ymddangos yn y tab Ffefrynnau a gellir eu tynnu ar unrhyw adeg.",
    "How do I change text size or switch themes?": "Sut ydw i'n newid maint y testun neu'r thema?",
    "Use the Accessibility settings above to adjust text size (80%–140%) or switch between Dark, Light, and High contrast themes. Your choices are saved automatically to your Listener ID.": "Defnyddiwch y gosodiadau hygyrchedd uchod i addasu maint y testun (80%–140%), yr iaith, neu newid rhwng themâu Tywyll, Golau a Chyferbyniad Uchel. Mae eich dewisiadau'n cael eu cadw'n awtomatig.",
    "Can I update or reset my listening survey?": "A allaf ddiweddaru neu ailosod fy arolwg gwrando?",
    "Yes — click Edit survey answers above to update your favourite genres (up to five) or preferred episode length, or click Reset survey to clear your saved preferences.": "Gallwch — cliciwch Golygu atebion yr arolwg uchod i ddiweddaru eich hoff genres (hyd at bump) neu hyd penodau, neu cliciwch Ailosod yr arolwg i glirio eich dewisiadau.",

    # Programme Detail page & Mini-bar
    "←  Back": "←  Yn ôl",
    "Save to favourites": "Cadw i ffefrynnau",
    "Remove from favourites": "Tynnu o ffefrynnau",
    "★  Rate this programme": "★  Graddio'r rhaglen hon",
    "Rate this programme": "Graddio'r rhaglen hon",
    "Update your rating": "Diweddaru eich sgôr",
    "Select a star rating from 1 to 5.": "Dewiswch sgôr seren rhwng 1 a 5.",
    "Save rating": "Cadw sgôr",
    "YOUR LISTENING": "EICH GWRANDO",
    "You haven't listened to this podcast yet.": "Nid ydych chi wedi gwrando ar y podlediad hwn eto.",
    "Not yet rated": "Heb ei graddio eto",
    "Playback is simulated": "Mae'r chwarae wedi'i efelychu",
    "You can't rate this programme until you've listened to it.": "Ni allwch raddio'r rhaglen hon nes i chi wrando arni.",
    "Save preferences": "Cadw dewisiadau",
    "Back to Home": "Yn ôl i'r Hafan",
    "SECRET EASTER EGG": "WY PASG CYFRINACHOL",
    "BBC Sounds Snake": "Neidr BBC Sounds",
    "BBC Sounds Card Match": "Cyfateb Cardiau BBC Sounds",
    "BBC Sounds Flappy Bird": "Flappy Bird BBC Sounds",
    "Activate easter egg": "Gweithredu wy pasg",
    "Easter egg activated ✓": "Wy pasg wedi'i weithredu ✓",
    'Activate the easter egg, then click all three letters of "BBC" (B, B, and C) in the top-left logo within 2 seconds to launch Snake.': 'Gweithredwch yr wy pasg, yna cliciwch bob un o dair llythyren "BBC" (B, B, a C) yn y logo ar frig chwith y ffenestr o fewn 2 eiliad i agor Neidr.',
    'Activated! Click all three letters of "BBC" (B, B, and C) in the top-left logo within 2 seconds to launch Snake.': 'Wedi\'i weithredu! Cliciwch bob un o dair llythyren "BBC" (B, B, a C) yn y logo ar frig chwith y ffenestr o fewn 2 eiliad i agor Neidr.',
    'Activate the easter egg, then click all three letters of "BBC" (B, B, and C) in the top-left logo within 2 seconds to launch Card Match.': 'Gweithredwch yr wy pasg, yna cliciwch bob un o dair llythyren "BBC" (B, B, a C) yn y logo ar frig chwith y ffenestr o fewn 2 eiliad i agor Cyfateb Cardiau.',
    'Activated! Click all three letters of "BBC" (B, B, and C) in the top-left logo within 2 seconds to launch Card Match.': 'Wedi\'i weithredu! Cliciwch bob un o dair llythyren "BBC" (B, B, a C) yn y logo ar frig chwith y ffenestr o fewn 2 eiliad i agor Cyfateb Cardiau.',
    'Activate the easter egg, then click all three letters of "BBC" (B, B, and C) in the top-left logo within 2 seconds to launch Flappy Bird.': 'Gweithredwch yr wy pasg, yna cliciwch bob un o dair llythyren "BBC" (B, B, a C) yn y logo ar frig chwith y ffenestr o fewn 2 eiliad i agor Flappy Bird.',
    'Activated! Click all three letters of "BBC" (B, B, and C) in the top-left logo within 2 seconds to launch Flappy Bird.': 'Wedi\'i weithredu! Cliciwch bob un o dair llythyren "BBC" (B, B, a C) yn y logo ar frig chwith y ffenestr o fewn 2 eiliad i agor Flappy Bird.',
}

_RE_GREETING = re.compile(r"^Good to have you back, (.+)!$")
_RE_LISTENER_ID = re.compile(r"^Listener ID  ·  (.+)$")
_RE_AVG = re.compile(r"^★ ([0-9.]+) / 5 average$")
_RE_PROGS = re.compile(r"^(\d+) programmes$")
_RE_PAGE = re.compile(r"^Page (\d+) of (\d+)$")
_RE_PLAYS = re.compile(r"^(\d+) plays?$")
_RE_SCALE = re.compile(r"^(\d+)%  ·  (Default|Larger|Smaller)$")
_RE_SAVED_NAME = re.compile(r'^Saved — Home will greet you as "Good to have you back, (.+)!"$')


def set_active_language(lang_code):
    """Set the active UI language ('en' or 'cy')."""
    global CURRENT_LANGUAGE
    CURRENT_LANGUAGE = "cy" if str(lang_code or "").lower() == "cy" else "en"
    return CURRENT_LANGUAGE


def translate(text):
    """Translate a UI string to Welsh (Cymraeg) when Welsh mode is active."""
    if CURRENT_LANGUAGE != "cy" or not isinstance(text, str) or not text:
        return text
    direct = TRANSLATIONS_CY.get(text)
    if direct is not None:
        return direct

    m = _RE_GREETING.match(text)
    if m:
        return f"Braf eich cael yn ôl, {m.group(1)}!"
    m = _RE_LISTENER_ID.match(text)
    if m:
        return f"ID Gwrandäwr  ·  {m.group(1)}"
    m = _RE_AVG.match(text)
    if m:
        return f"★ {m.group(1)} / 5 cyfartaledd"
    m = _RE_PROGS.match(text)
    if m:
        return f"{m.group(1)} o raglenni"
    m = _RE_PAGE.match(text)
    if m:
        return f"Tudalen {m.group(1)} o {m.group(2)}"
    m = _RE_PLAYS.match(text)
    if m:
        n = int(m.group(1))
        return f"{n} gwrandawiad" if n == 1 else f"{n} o wrandawiadau"
    m = _RE_SCALE.match(text)
    if m:
        kind = {"Default": "Rhagosodedig", "Larger": "Mwy", "Smaller": "Llai"}[m.group(2)]
        return f"{m.group(1)}%  ·  {kind}"
    m = _RE_SAVED_NAME.match(text)
    if m:
        return f'Wedi cadw — bydd yr Hafan yn eich cyfarch fel "Braf eich cael yn ôl, {m.group(1)}!"'
    if text.startswith("Last played"):
        out = text.replace("Last played", "Chwaraewyd ddiwethaf", 1)
        out = out.replace("average", "cyfartaledd").replace("Not yet rated", "Heb ei graddio eto")
        return out
    return text
