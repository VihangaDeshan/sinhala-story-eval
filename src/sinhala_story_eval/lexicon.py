# -*- coding: utf-8 -*-
"""
Sinhala register markers — the rule data behind DARC.

These are DATA, not heuristics tuned to this corpus. They are derived from
the documented grammar of Sinhala diglossia:

    "subject-verb agreement is present in literary Sinhala but does not
     occur in spoken Sinhala"
     — Gair (1986), as cited in Mawelle (2023); Zubair (2010)

TWO TIERS
---------
Tier A endings occur ONLY on finite verbs, so they fire on sight.
Tier B endings also occur on nouns and adjectives, so they fire only when
what remains after stripping the suffix is a recognised verb root. Without
that guard, පියා (father) and දරුවා (child) are tagged as spoken verbs, and
සති (weeks) and නැති (absent) as literary ones — the v1 defect, which ran at
6–10% false positives on real LLM output.

THE -යි AMBIGUITY
-----------------
-යි marks BOTH the literary 3sg present and the spoken predicative:

    verb stem           → LITERARY    කරයි, දිදුලයි
    adjective/noun stem → SPOKEN      හොඳයි, කැමතියි

Resolved by stem type in classify.py. This is a real grammatical
distinction, not a workaround.

Counts are unchanged from v3 and must stay that way unless a rule change is
deliberate and logged: the v4 release altered segmentation only.
"""

LIT_SUF_A = ["ේය","ාය","ීය","ිණි","ුණි","ූහ","න්නේය","ෙමි","ුමු","ෝය"]

SPO_SUF_A = ["නවා","ෙනවා","න්නවා","ුනා","ුණා","න්නා","ක්කා","ෙව්වා"]

LIT_SUF_B = ["යි","ති","යහ","ළහ","ුහ","ෙති"]

SPO_SUF_B = ["ියා","ත්තා","ුවා","ළා","වා","ලා"]


# Irregular and very short forms the suffix rules cannot reach
LIT_EXACT = {"විය","වූහ","වී","වූයේ","ගියහ","කළහ","වෙති","ඇත","නැත","වෙයි","යති",
             "එති","සිටිති","නොවීය","නොවේ","නොවිණි","කරති","දුටුවේය","දුටුවාය"}

SPO_EXACT = {"ආවා","ගියා","කළා","දුන්නා","ගත්තා","වුනා","වුණා","තියෙනවා","ඉන්නවා",
             "දන්නෑ","ආවෙ","හිටියා","දැක්කා","ගැයුවා","හොඳයි","කැමතියි","ආදරෙයි",
             "එහෙමයි","ඕනෙයි","දන්නෙ","ඇහුවා","කිව්වා"}


# Pronouns and particles that differ sharply by register
LIT_FUNC = {"ඔහු","ඇය","ඔවුහු","ඔවුන්","මා","ඔබ","තෙමේ","මෙය","එය","මොහු",
            "එහෙයින්","එබැවින්","ඔහුගේ","ඇගේ","ඔවුන්ගේ","මාගේ","ඔබගේ","ඔහුට",
            "ඇයට","එහි","මෙහි","එහිදී","එසේය","මෙසේ","මැනවි","ද"}

SPO_FUNC = {"එයා","එයාලා","ඔයා","ඔයාලා","මම","මට","අපි","මේක","ඒක","ඕක","නෑ",
            "නැහැ","ඔව්","වගේ","කියලා","ගොඩක්","මොකද","එහෙම","තමයි","පුළුවන්",
            "බෑ","හරි","ඉතින්","අනේ","නේද","මොනවා","කොහොමද","එයාගෙ","ඔයාගෙ",
            "මගෙ","අපේ","මෙහෙ","එහෙදි","කොහෙද","මොකක්ද","අලුත්ද","ඊයෙ","උදේ",
            "එපා","ඕන","ඔයාව","ඔයාට","මාව"}


# Closed inventory of high-frequency verb roots — the Tier B guard
VERB_ROOTS = {
 # motion / existence
 "ය","යන","ගි","ගිය","එ","එන","ආ","වැටු","වැටි","පැමිණි","පැමිණ","දිව","ඇවිද",
 "වු","වූ","වෙ","වෙන","තිබ","තිබු","තිබි","සිටි","හිටි","ඉන්","ඉඳ","තියෙ","නවත්",
 # speech / perception / cognition
 "කිය","කිව්","කී","ඇසු","ඇහු","අස","දැ","දැක","දැක්","දුටු","දකි","බල","බැලු","බැලී",
 "පෙන","පෙනු","පෙනි","දැන","දන්","හඳුන","තේරු","තේරි","හිත","සිත",
 # transfer / action
 "දෙ","දුන්","ගන්","ගත්","ලැබ","ලැබු","ලැබි","කර","කළ","කෙරු","කරන",
 "ගැහ","ගහ","ගැය","ගය","හද","හැදු","ලිය","ලිව්","කන","බොන","නෙළ","ඉගෙන",
 "පිළිගත්","ඉදිකර","වැන්ද","වැඳ","පටන්ගත්","හම්බ","නැගිටි",
 # emotion / change of state
 "සිනාසෙ","හඬ","අඬ","දිදුල","ගෙවු","ගෙවි","පැතිරු","පැතිරි","වැදු","වැදි",
 "බැබළු","බැබළි","වැඩු","වැඩි","ඉපදු","මිය","නැසු",
 "ඉල්ල","ඉල්ලු","නැට","නැටු","හැඬ","හැඬු","නැළ","නැළෙව්","සැරස","සැරසු",
 "කැළඹ","කැළඹු","පිප","පිපු","නැග","නැගු","සැඟව","හැංග","තෙරප","තෙරපු",
 "අඳ","ඇඳ","හොය","හෙව්","මක","මැක","අර","ඇර","වහ","වැහ","තබ","තැබ",
}


# Register-neutral: identical in both varieties, must never be tagged
NEUTRAL = {
 "දැන්","බලා","ගලා","දක්වා","පියා","දරුවා","තාත්තා","අම්මා","සති","නැති","කැමති",
 "ගති","මිය","කා","තේ","කුඩා","දිනපතා","වැඩි","වාඩි","ඉතිරි","වතුයාය","වතුයායේ",
 "කතා","මාලා","වේලා","සීමා","භාෂා","සේවා","ක්‍රියා","රාත්‍රිය","ගොවියා","තරුණයා",
 "මිනිසා","ළමයා","නායකයා","සිසුවා","ගමනා","බෝලා","කාලා","දුව","සියල්ල","මංගල්‍යය",
 "ප්‍රේමය","ආදරය","සතුට","දුක","ජීවිතය","ගම","නිවස","පවුල","මව",
 "දෙපළා","දෙපොළා","කණ්ණාඩියා","ගුරුවරයා","වෛද්‍යවරයා","ගැහැණියා","වෙනුවා",
}

