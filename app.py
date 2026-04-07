import os
import json
import anthropic
from flask import Flask, request, jsonify, send_file, render_template
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, Image as RLImage
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
import tempfile
import re
import traceback

app = Flask(__name__)

GOLD      = colors.HexColor("#F5A800")
BLACK     = colors.HexColor("#1A1A1A")
OFF_WHITE = colors.HexColor("#F9F7F2")
RULE_GREY = colors.HexColor("#E0D8C8")
MID_GREY  = colors.HexColor("#666666")
DARK_GREY = colors.HexColor("#222222")
WHITE     = colors.white
TECH_COL  = colors.HexColor("#1e7a35")
TECH_BG   = colors.HexColor("#f0f9f3")
PHYS_COL  = colors.HexColor("#9a6a00")
PHYS_BG   = colors.HexColor("#fdf8ec")
PSYCH_COL = colors.HexColor("#2255cc")
PSYCH_BG  = colors.HexColor("#f0f4ff")
SOC_COL   = colors.HexColor("#b52200")
SOC_BG    = colors.HexColor("#fff4f1")
DEV_COL   = colors.HexColor("#1565C0")
SEC_COL   = colors.HexColor("#F9A825")
EXC_COL   = colors.HexColor("#2E7D32")

GRADE_LABELS = {1:"Needs Support",2:"Developing",3:"Good",4:"Very Good",5:"Excellent"}

CORNERS_DEF = [
    ("technical",    "Technical / Tactical", TECH_COL, TECH_BG),
    ("physical",     "Physical",             PHYS_COL, PHYS_BG),
    ("psychological","Psychological",        PSYCH_COL,PSYCH_BG),
    ("social",       "Social",               SOC_COL,  SOC_BG),
]

CORNER_ITEMS = {
    "technical": [
        "First touch and ball control","Dribbling and ball manipulation",
        "Passing accuracy and weight","Scanning before receiving",
        "Decision-making in possession","Retaining possession under pressure",
        "Defensive positioning and body shape","Understanding transitions",
        "Position-specific responsibilities",
    ],
    "physical": [
        "Agility and coordination","Acceleration and speed","Strength in duels",
        "Balance and stability","Endurance and work rate","Movement efficiency",
        "Position-specific physical demands",
    ],
    "psychological": [
        "Focus and concentration","Resilience after mistakes","Confidence in possession",
        "Willingness to take responsibility","Game understanding and anticipation",
        "Leadership behaviours","Motivation and attitude",
        "Consistency across training and matches",
    ],
    "social": [
        "Communication with teammates","Calling for the ball with purpose",
        "Supporting and organising others","Respect for coaches, referees, teammates",
        "Teamwork and cooperation","Contribution to team environment",
        "Ability to work in groups",
    ],
}


def sty(name, **kw):
    return ParagraphStyle(name, **kw)


def build_pdf(data, output_path):
    doc = SimpleDocTemplate(output_path, pagesize=A4,
        leftMargin=12*mm, rightMargin=12*mm, topMargin=10*mm, bottomMargin=12*mm)
    W = 186*mm
    foundation = data.get("isFoundation", False)

    styles = {
        "title":   sty("t",  fontName="Helvetica-Bold", fontSize=18, textColor=GOLD, alignment=TA_CENTER, leading=22),
        "subtitle":sty("s",  fontName="Helvetica", fontSize=9, textColor=colors.HexColor("#aaaaaa"), alignment=TA_CENTER, leading=13),
        "pl":      sty("pl", fontName="Helvetica-Bold", fontSize=8, textColor=MID_GREY, leading=10),
        "pv":      sty("pv", fontName="Helvetica-Bold", fontSize=12, textColor=DARK_GREY, leading=15),
        "sec":     sty("sec",fontName="Helvetica-Bold", fontSize=8, textColor=MID_GREY, spaceAfter=3, leading=10),
        "body":    sty("b",  fontName="Helvetica", fontSize=9.5, textColor=DARK_GREY, leading=15, spaceAfter=4),
        "ri":      sty("ri", fontName="Helvetica", fontSize=9, textColor=DARK_GREY, leading=13),
        "ov_body": sty("ob", fontName="Helvetica", fontSize=10, textColor=WHITE, leading=16),
        "bl":      sty("bl", fontName="Helvetica-Bold", fontSize=8.5, textColor=MID_GREY, spaceAfter=2, leading=11),
        "gk":      sty("gk", fontName="Helvetica", fontSize=8, textColor=MID_GREY, leading=11),
    }

    story = []

    # Header
    logo_path = os.path.join(os.path.dirname(__file__), "static", "logo.png")
    logo_cell = RLImage(logo_path, width=16*mm, height=16*mm) if os.path.exists(logo_path) else Paragraph("", styles["pl"])
    hdr = Table([[
        logo_cell,
        [Paragraph("FALMOUTH COMMUNITY YOUTH FC", styles["title"]),
         Paragraph("Player Review  -  FA Four Corner Model", styles["subtitle"])],
        Paragraph("", styles["pl"]),
    ]], colWidths=[20*mm, 146*mm, 20*mm])
    hdr.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),BLACK),
        ("TOPPADDING",(0,0),(-1,-1),10),("BOTTOMPADDING",(0,0),(-1,-1),10),
        ("LEFTPADDING",(0,0),(-1,-1),8),("RIGHTPADDING",(0,0),(-1,-1),8),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("LINEBELOW",(0,0),(-1,-1),3,GOLD),
    ]))
    story += [hdr, Spacer(1,4*mm)]

    # Player info
    def ic(lbl, val):
        return [Paragraph(lbl, styles["pl"]), Paragraph(val or "-", styles["pv"])]
    info = Table([[
        ic("PLAYER", data["name"]),
        ic("POSITION", data["position"]),
        ic("COACH", data["coach"]),
        ic("AGE GROUP", data.get("agegroup","")),
        ic("REVIEW", data["season"]),
    ]], colWidths=[W/5]*5)
    info.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),OFF_WHITE),("BOX",(0,0),(-1,-1),.5,RULE_GREY),
        ("LINEAFTER",(0,0),(-2,-1),.5,RULE_GREY),
        ("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8),
        ("LEFTPADDING",(0,0),(-1,-1),8),("RIGHTPADDING",(0,0),(-1,-1),8),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
    ]))
    story += [info, Spacer(1,4*mm)]

    # Grade key
    if foundation:
        gk = Table([[
            Paragraph("GRADE KEY:", styles["gk"]),
            Paragraph("Developing", sty("gd", fontName="Helvetica-Bold", fontSize=8, textColor=DEV_COL, leading=11)),
            Paragraph("Secure", sty("gs", fontName="Helvetica-Bold", fontSize=8, textColor=SEC_COL, leading=11)),
            Paragraph("Excelling", sty("ge", fontName="Helvetica-Bold", fontSize=8, textColor=EXC_COL, leading=11)),
        ]], colWidths=[30*mm, 50*mm, 50*mm, 56*mm])
    else:
        gk_text = "  ".join(["%d = %s" % (k,v) for k,v in GRADE_LABELS.items()])
        gk = Table([[Paragraph("GRADE KEY:  " + gk_text, styles["gk"])]], colWidths=[W])
    gk.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),OFF_WHITE),("BOX",(0,0),(-1,-1),.5,RULE_GREY),
        ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
        ("LEFTPADDING",(0,0),(-1,-1),10),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
    ]))
    story += [gk, Spacer(1,4*mm)]

    # Four corners
    for key, title, col, bg in CORNERS_DEF:
        items_scores = data["corners"][key]["items"]
        strengths    = data["corners"][key]["strengths"]
        develop      = data["corners"][key]["develop"]
        elems = []

        if foundation:
            hdr_tbl = Table([[
                Paragraph(title, sty("ch", fontName="Helvetica-Bold", fontSize=13, textColor=WHITE, leading=16)),
            ]], colWidths=[W])
        else:
            scores_only = [s for _,s in items_scores if isinstance(s,int)]
            avg = sum(scores_only)/len(scores_only) if scores_only else 0
            hdr_tbl = Table([[
                Paragraph(title, sty("ch", fontName="Helvetica-Bold", fontSize=13, textColor=WHITE, leading=16)),
                Paragraph("<b>%.1f</b>" % avg, sty("ca", fontName="Helvetica-Bold", fontSize=22, textColor=WHITE, alignment=TA_RIGHT, leading=26)),
            ]], colWidths=[130*mm, 30*mm])

        hdr_tbl.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,-1),col),
            ("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8),
            ("LEFTPADDING",(0,0),(-1,-1),10),("RIGHTPADDING",(0,0),(-1,-1),10),
            ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ]))
        elems.append(hdr_tbl)

        rows = []
        col_hex = "#%02x%02x%02x" % (int(col.red*255), int(col.green*255), int(col.blue*255))
        for item, score in items_scores:
            if foundation:
                if score == "D":
                    badge = Paragraph("<b>Developing</b>", sty("fd", fontName="Helvetica-Bold", fontSize=9, textColor=DEV_COL, leading=13))
                elif score == "S":
                    badge = Paragraph("<b>Secure</b>", sty("fs", fontName="Helvetica-Bold", fontSize=9, textColor=SEC_COL, leading=13))
                elif score == "E":
                    badge = Paragraph("<b>Excelling</b>", sty("fe", fontName="Helvetica-Bold", fontSize=9, textColor=EXC_COL, leading=13))
                else:
                    badge = Paragraph("-", styles["ri"])
                rows.append([Paragraph("- %s" % item, styles["ri"]), badge])
            else:
                score_int = score if isinstance(score,int) else 0
                label = GRADE_LABELS.get(score_int,"")
                dots_on  = '<font color="%s">%s</font>' % (col_hex, "●" * score_int)
                dots_off = '<font color="#cccccc">%s</font>' % ("●" * (5-score_int))
                rows.append([
                    Paragraph("- %s" % item, styles["ri"]),
                    Paragraph(dots_on + dots_off, sty("d", fontName="Helvetica", fontSize=10, leading=13)),
                    Paragraph("<b>%d</b> <font color='#888'>%s</font>" % (score_int, label),
                        sty("sc", fontName="Helvetica", fontSize=8.5, leading=13, alignment=TA_RIGHT)),
                ])

        col_widths = [120*mm, 60*mm] if foundation else [90*mm, 40*mm, 30*mm]
        rt = Table(rows, colWidths=col_widths)
        rt.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,-1),bg),
            ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),
            ("LEFTPADDING",(0,0),(0,-1),10),("LEFTPADDING",(1,0),(1,-1),4),
            ("RIGHTPADDING",(-1,0),(-1,-1),10),
            ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
            ("LINEBELOW",(0,0),(-1,-2),.3,RULE_GREY),
        ]))
        elems.append(rt)

        txt = Table([[
            [Paragraph("STRENGTHS", styles["sec"]), Paragraph(strengths, styles["body"])],
            [Paragraph("AREAS TO DEVELOP", styles["sec"]), Paragraph(develop, styles["body"])],
        ]], colWidths=[82*mm,82*mm])
        txt.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,-1),WHITE),
            ("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8),
            ("LEFTPADDING",(0,0),(0,-1),10),("LEFTPADDING",(1,0),(1,-1),12),
            ("RIGHTPADDING",(0,0),(0,-1),12),("RIGHTPADDING",(-1,0),(-1,-1),10),
            ("VALIGN",(0,0),(-1,-1),"TOP"),
            ("LINEAFTER",(0,0),(0,-1),.5,RULE_GREY),
            ("BOX",(0,0),(-1,-1),.5,RULE_GREY),
        ]))
        elems.append(txt)
        elems.append(Spacer(1,6*mm))
        story.append(KeepTogether(elems))

    # Overall comment
    ov = Table([[
        [Paragraph("OVERALL COACH COMMENT", sty("ovh", fontName="Helvetica-Bold", fontSize=10, textColor=GOLD, leading=14, spaceAfter=6)),
         Paragraph(data["overall"], styles["ov_body"])]
    ]], colWidths=[W])
    ov.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),BLACK),("BOX",(0,0),(-1,-1),2,GOLD),
        ("TOPPADDING",(0,0),(-1,-1),12),("BOTTOMPADDING",(0,0),(-1,-1),12),
        ("LEFTPADDING",(0,0),(-1,-1),14),("RIGHTPADDING",(0,0),(-1,-1),14),
        ("VALIGN",(0,0),(-1,-1),"TOP"),
    ]))
    story += [ov, Spacer(1,5*mm)]

    def blank(lbl):
        elems = []
        if lbl:
            elems.append(Paragraph(lbl, styles["bl"]))
        elems.append(Table([[Paragraph("",styles["body"])]], colWidths=[W], rowHeights=[14*mm],
            style=[("BOX",(0,0),(-1,-1),.5,RULE_GREY),("BACKGROUND",(0,0),(-1,-1),OFF_WHITE)]))
        elems.append(Spacer(1,3*mm))
        return elems

    story.append(Paragraph("PLAYER REFLECTIONS", sty("prh", fontName="Helvetica-Bold", fontSize=10, textColor=MID_GREY, leading=13, spaceAfter=4)))
    story += blank("What I have enjoyed most this season:")
    story += blank("Something I want to get better at:")
    story += blank("My goal for next term / season:")
    story.append(Paragraph("PARENT / GUARDIAN COMMENTS", sty("pgh", fontName="Helvetica-Bold", fontSize=10, textColor=MID_GREY, leading=13, spaceAfter=4)))
    story += blank("")

    doc.build(story)


def get_ai_text(body):
    name         = body.get("name","Player")
    position     = body.get("position","")
    coach        = body.get("coach","")
    team         = body.get("team","")
    season       = body.get("season","Mid Season Review")
    agegroup     = body.get("agegroup","U12")
    foundation   = body.get("isFoundation", False)
    ratings_text = body.get("ratingsText","")
    note_comment = body.get("noteComment","")
    note_strength= body.get("noteStrength","")
    note_develop = body.get("noteDevelop","")

    age_guidance = {
        "U7":  "Very young player (5-7). Very simple fun celebratory language. Short sentences. Focus on enjoyment and effort only.",
        "U8":  "Young player (7-8). Simple fun encouraging language. Celebrate effort and enjoyment.",
        "U9":  "Player is 8-9. Warm encouraging language. Focus on fun basic skills and effort.",
        "U10": "Player is 9-10. Encouraging language. Focus on developing skills and enjoyment.",
        "U11": "Player is 10-11. Clear encouraging language. Begin simple tactical ideas. Positive and supportive.",
        "U12": "Player is 11-12. Clear encouraging language with some tactical awareness. Balance praise with simple development points.",
        "U13": "Player is 12-13. More detailed tactical language. Honest constructive feedback alongside praise.",
        "U14": "Player is 13-14. Detailed tactical and technical language. Specific honest feedback alongside praise.",
        "U15": "Player is 14-15. Mature detailed tactical language. Specific technical and tactical development areas.",
        "U16": "Player is 15-16. Mature detailed language. Treat them as developing adults.",
    }

    if foundation:
        rating_system = "Ratings use: Developing / Secure / Excelling. Reference these descriptors in your text rather than numbers."
    else:
        rating_system = "Ratings use 1-5. Praise scores of 4-5. Encourage development on scores of 1-2."

    parts = [
        "Write a FA Four Corner Model player review for Falmouth Community Youth Football Club.",
        "Player: %s | Position: %s | Coach: %s | Team: %s | Age Group: %s | Review: %s" % (name, position, coach, team, agegroup, season),
        "AGE GUIDANCE: %s" % age_guidance.get(agegroup,""),
        "RATING SYSTEM: %s" % rating_system,
        "RATINGS:",
        ratings_text,
    ]
    if note_comment: parts.append("Coach comment: %s" % note_comment)
    if note_strength: parts.append("Key strengths: %s" % note_strength)
    if note_develop: parts.append("Development focus: %s" % note_develop)
    parts.append('Return ONLY valid JSON, no markdown: {"technical_strengths":"...","technical_develop":"...","physical_strengths":"...","physical_develop":"...","psychological_strengths":"...","psychological_develop":"...","social_strengths":"...","social_develop":"...","overall":"..."}')
    parts.append("Use %s first name throughout. Match language to age group." % name)

    prompt = "\n".join(parts)

    api_key = os.environ.get("ANTHROPIC_API_KEY","")
    if not api_key:
        raise Exception("ANTHROPIC_API_KEY not set")

    client = anthropic.Anthropic(api_key=api_key, timeout=60.0)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        messages=[{"role":"user","content": prompt}]
    )
    raw = message.content[0].text.strip()
    print("AI: " + raw[:200], flush=True)
    raw = re.sub(r"```json","",raw)
    raw = re.sub(r"```","",raw)
    return json.loads(raw.strip())


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate_text", methods=["POST"])
def generate_text():
    try:
        body = request.get_json()
        ai = get_ai_text(body)
        return jsonify(ai)
    except json.JSONDecodeError as e:
        print("JSON ERROR: " + str(e), flush=True)
        return jsonify({"error": "Response error - please try again"}), 500
    except Exception as e:
        print("ERROR: " + traceback.format_exc(), flush=True)
        return jsonify({"error": "%s: %s" % (type(e).__name__, str(e))}), 500


@app.route("/generate_pdf", methods=["POST"])
def generate_pdf():
    try:
        body = request.get_json()
        name       = body.get("name","Player")
        ratings_text = body.get("ratingsText","")
        foundation = body.get("isFoundation", False)

        def parse_scores(corner_key):
            items = CORNER_ITEMS[corner_key]
            scores = []
            for item in items:
                pattern = re.compile(re.escape("* " + item) + r":\s*(.+)", re.IGNORECASE)
                m = pattern.search(ratings_text)
                if m:
                    val = m.group(1).strip()
                    if foundation:
                        code_map = {"Developing":"D","Secure":"S","Excelling":"E"}
                        scores.append((item, code_map.get(val, "D")))
                    else:
                        try:
                            scores.append((item, int(val[0])))
                        except:
                            scores.append((item, 3))
                else:
                    scores.append((item, "D" if foundation else 3))
            return scores

        data = {
            "name": name,
            "position": body.get("position",""),
            "coach": body.get("coach",""),
            "team": body.get("team",""),
            "season": body.get("season",""),
            "agegroup": body.get("agegroup",""),
            "isFoundation": foundation,
            "overall": body.get("overall",""),
            "corners": {
                "technical":    {"items":parse_scores("technical"),    "strengths":body.get("technical_strengths",""),    "develop":body.get("technical_develop","")},
                "physical":     {"items":parse_scores("physical"),     "strengths":body.get("physical_strengths",""),     "develop":body.get("physical_develop","")},
                "psychological":{"items":parse_scores("psychological"),"strengths":body.get("psychological_strengths",""),"develop":body.get("psychological_develop","")},
                "social":       {"items":parse_scores("social"),       "strengths":body.get("social_strengths",""),       "develop":body.get("social_develop","")},
            }
        }

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            pdf_path = f.name
        build_pdf(data, pdf_path)

        return send_file(pdf_path, as_attachment=True,
            download_name="%s_Player_Review.pdf" % name.replace(" ","_"),
            mimetype="application/pdf")

    except Exception as e:
        print("PDF ERROR: " + traceback.format_exc(), flush=True)
        return jsonify({"error": "%s: %s" % (type(e).__name__, str(e))}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
