import os
import json
import anthropic
from flask import Flask, request, jsonify, send_file, render_template_string
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
import tempfile
import re

app = Flask(__name__)

# ── Colours ───────────────────────────────────────────────────────────────────
DARK_GREEN  = colors.HexColor("#1a3a22")
MID_GREEN   = colors.HexColor("#2d8a47")
LIGHT_GREEN = colors.HexColor("#3daa5a")
GOLD        = colors.HexColor("#c8960a")
TECH_GREEN  = colors.HexColor("#1e7a35")
TECH_BG     = colors.HexColor("#f0f9f3")
PHYS_AMBER  = colors.HexColor("#9a6a00")
PHYS_BG     = colors.HexColor("#fdf8ec")
PSYCH_BLUE  = colors.HexColor("#2255cc")
PSYCH_BG    = colors.HexColor("#f0f4ff")
SOC_RED     = colors.HexColor("#b52200")
SOC_BG      = colors.HexColor("#fff4f1")
OFF_WHITE   = colors.HexColor("#f8f9f8")
RULE_GREY   = colors.HexColor("#dddddd")
MID_GREY    = colors.HexColor("#666666")
DARK_GREY   = colors.HexColor("#222222")

GRADE_LABELS = {1:"Needs Support",2:"Developing",3:"Good",4:"Very Good",5:"Excellent"}

CORNERS_DEF = [
    ("technical",    "Technical / Tactical", "⚙", TECH_GREEN,  TECH_BG),
    ("physical",     "Physical",             "💪", PHYS_AMBER,  PHYS_BG),
    ("psychological","Psychological",         "🧠", PSYCH_BLUE,  PSYCH_BG),
    ("social",       "Social",               "🤝", SOC_RED,     SOC_BG),
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

# ── HTML PAGE ─────────────────────────────────────────────────────────────────
HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Player Review Tool</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,sans-serif;background:#f2f5f3;min-height:100vh;color:#111}
header{background:#1a3a22;padding:16px 20px;display:flex;align-items:center;gap:12px;position:sticky;top:0;z-index:100;border-bottom:2px solid #3daa5a}
header h1{color:white;font-size:18px;font-weight:800;letter-spacing:.5px}
header p{color:#7ab88a;font-size:11px;letter-spacing:1px;margin-top:2px}
.wrap{max-width:700px;margin:0 auto;padding:20px 14px}
.card{background:white;border-radius:10px;border:1px solid #e4e8e4;box-shadow:0 1px 5px rgba(0,0,0,.06);margin-bottom:16px}
.card-head{padding:13px 18px;border-bottom:1px solid #f0f0f0;font-weight:800;font-size:12px;text-transform:uppercase;letter-spacing:1px;color:#1a3a22}
.card-body{padding:14px 18px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:12px}
label{display:block;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#666;margin-bottom:5px}
input,select,textarea{width:100%;padding:9px 11px;border:1.5px solid #ddd;border-radius:6px;font-size:14px;color:#111;background:#fafafa;font-family:inherit}
textarea{resize:vertical;line-height:1.6}
.corner-header{display:flex;align-items:center;gap:10px;padding:13px 18px;border-radius:10px 10px 0 0}
.corner-avg{margin-left:auto;font-size:26px;font-weight:900}
.corner-title{font-weight:800;font-size:15px;color:#111}
.rating-row{display:flex;align-items:center;justify-content:space-between;padding:9px 0;border-bottom:1px solid #f2f2f2;gap:10px}
.rating-row:last-child{border-bottom:none}
.rating-label{font-size:14px;color:#222;flex:1}
.stars{display:flex;gap:5px;flex-shrink:0}
.star{width:32px;height:32px;border:2px solid #ddd;border-radius:6px;background:white;color:#aaa;font-weight:700;font-size:13px;cursor:pointer;transition:all .1s;display:flex;align-items:center;justify-content:center}
.grade-key{background:white;border-radius:8px;border:1px solid #e4e8e4;padding:10px 18px;margin-bottom:16px;display:flex;gap:18px;flex-wrap:wrap;align-items:center;font-size:12px;color:#555}
.grade-key strong{color:#111}
.btn-generate{width:100%;padding:16px;background:#1e7a35;color:white;border:none;border-radius:9px;font-size:16px;font-weight:800;cursor:pointer;letter-spacing:.5px;transition:background .2s}
.btn-generate:hover{background:#2d8a47}
.btn-generate:disabled{background:#aaa;cursor:not-allowed}
.status{margin-top:12px;padding:12px 16px;border-radius:8px;font-size:14px;display:none;text-align:center}
.status.loading{background:#e8f5ec;color:#1e7a35;display:block}
.status.error{background:#fde8e8;color:#b52200;display:block}
.status.success{background:#e8f5ec;color:#1e7a35;display:block}
.progress{width:100%;height:4px;background:#ddd;border-radius:2px;margin-top:8px;display:none}
.progress-bar{height:4px;background:#1e7a35;border-radius:2px;width:0;transition:width .3s}
</style>
</head>
<body>
<header>
  <div>
    <h1>⚽ Player Review Tool</h1>
    <p>FA FOUR CORNER MODEL</p>
  </div>
</header>
<div class="wrap">

  <!-- Player Details -->
  <div class="card">
    <div class="card-head">Player Details</div>
    <div class="card-body">
      <div class="grid2">
        <div><label>Player Name</label><input id="name" placeholder="e.g. Rowan"></div>
        <div><label>Position</label><input id="position" placeholder="e.g. Midfield"></div>
        <div><label>Coach</label><input id="coach" placeholder="e.g. Darren"></div>
        <div><label>Team</label><input id="team" placeholder="e.g. U12 Ravens"></div>
      </div>
      <div style="margin-top:12px">
        <label>Review Period</label>
        <select id="season">
          <option>Mid Season Review</option>
          <option>End of Season Review</option>
          <option>Pre-Season Review</option>
          <option>Quarterly Review</option>
        </select>
      </div>
    </div>
  </div>

  <!-- Grade Key -->
  <div class="grade-key">
    <strong>Grade:</strong>
    <span><strong>1</strong> Needs Support</span>
    <span><strong>2</strong> Developing</span>
    <span><strong>3</strong> Good</span>
    <span><strong>4</strong> Very Good</span>
    <span><strong>5</strong> Excellent</span>
  </div>

  <!-- Corner cards built by JS -->
  <div id="corners"></div>

  <!-- Coach Notes -->
  <div class="card">
    <div class="card-head">Coach Notes <span style="color:#aaa;font-weight:400;text-transform:none;letter-spacing:0">(optional — helps personalise the report)</span></div>
    <div class="card-body">
      <div style="margin-bottom:12px"><label>Overall Comment</label><textarea id="note_comment" rows="2" placeholder="e.g. A really positive season so far..."></textarea></div>
      <div class="grid2">
        <div><label>Key Strengths</label><textarea id="note_strengths" rows="2" placeholder="e.g. Great attitude, strong defensively..."></textarea></div>
        <div><label>Development Focus</label><textarea id="note_develop" rows="2" placeholder="e.g. Improve transition speed..."></textarea></div>
      </div>
    </div>
  </div>

  <button class="btn-generate" id="generateBtn" onclick="generateReport()">⚡ Generate Report & Download PDF</button>
  <div class="progress" id="progress"><div class="progress-bar" id="progressBar"></div></div>
  <div class="status" id="status"></div>

</div>

<script>
const CORNERS = [
  {key:"technical",  label:"Technical / Tactical", icon:"⚙️", color:"#1e7a35", bg:"#f0f9f3",
   items:["First touch and ball control","Dribbling and ball manipulation","Passing accuracy and weight","Scanning before receiving","Decision-making in possession","Retaining possession under pressure","Defensive positioning and body shape","Understanding transitions","Position-specific responsibilities"]},
  {key:"physical",   label:"Physical",              icon:"💪", color:"#9a6a00", bg:"#fdf8ec",
   items:["Agility and coordination","Acceleration and speed","Strength in duels","Balance and stability","Endurance and work rate","Movement efficiency","Position-specific physical demands"]},
  {key:"psychological",label:"Psychological",       icon:"🧠", color:"#2255cc", bg:"#f0f4ff",
   items:["Focus and concentration","Resilience after mistakes","Confidence in possession","Willingness to take responsibility","Game understanding and anticipation","Leadership behaviours","Motivation and attitude","Consistency across training and matches"]},
  {key:"social",     label:"Social",                icon:"🤝", color:"#b52200", bg:"#fff4f1",
   items:["Communication with teammates","Calling for the ball with purpose","Supporting and organising others","Respect for coaches, referees, teammates","Teamwork and cooperation","Contribution to team environment","Ability to work in groups"]},
];

const ratings = {};
CORNERS.forEach(c => { ratings[c.key] = {}; c.items.forEach((_,i) => ratings[c.key][i] = 0); });

function buildCorners() {
  const wrap = document.getElementById("corners");
  CORNERS.forEach(c => {
    const div = document.createElement("div");
    div.className = "card";
    div.style.marginBottom = "16px";
    div.innerHTML = `
      <div class="corner-header" style="background:${c.bg};border-bottom:2px solid ${c.color}25">
        <span style="font-size:20px">${c.icon}</span>
        <span class="corner-title">${c.label}</span>
        <span class="corner-avg" style="color:${c.color}" id="avg_${c.key}">–</span>
      </div>
      <div class="card-body">
        ${c.items.map((item,i) => `
          <div class="rating-row">
            <span class="rating-label">${item}</span>
            <div class="stars" id="stars_${c.key}_${i}">
              ${[1,2,3,4,5].map(n=>`<div class="star" onclick="rate('${c.key}',${i},${n})" onmouseenter="hover('${c.key}',${i},${n},true)" onmouseleave="hover('${c.key}',${i},${n},false)">${n}</div>`).join("")}
            </div>
          </div>`).join("")}
      </div>`;
    wrap.appendChild(div);
  });
}

function rate(key, idx, val) {
  ratings[key][idx] = ratings[key][idx] === val ? 0 : val;
  renderStars(key, idx, ratings[key][idx]);
  updateAvg(key);
}

function hover(key, idx, val, on) {
  const current = ratings[key][idx];
  const stars = document.querySelectorAll(`#stars_${key}_${idx} .star`);
  const corner = CORNERS.find(c => c.key === key);
  stars.forEach((s, i) => {
    const active = i < (on ? val : current);
    s.style.borderColor = active ? corner.color : "#ddd";
    s.style.background  = active ? corner.color : "white";
    s.style.color       = active ? "white" : "#aaa";
  });
}

function renderStars(key, idx, val) {
  const corner = CORNERS.find(c => c.key === key);
  const stars = document.querySelectorAll(`#stars_${key}_${idx} .star`);
  stars.forEach((s, i) => {
    const active = i < val;
    s.style.borderColor = active ? corner.color : "#ddd";
    s.style.background  = active ? corner.color : "white";
    s.style.color       = active ? "white" : "#aaa";
  });
}

function updateAvg(key) {
  const vals = Object.values(ratings[key]).filter(v => v > 0);
  const avg = vals.length ? (vals.reduce((a,b)=>a+b,0)/vals.length).toFixed(1) : "–";
  document.getElementById(`avg_${key}`).textContent = avg;
}

function showStatus(msg, type) {
  const el = document.getElementById("status");
  el.textContent = msg;
  el.className = `status ${type}`;
}

function setProgress(pct) {
  document.getElementById("progress").style.display = "block";
  document.getElementById("progressBar").style.width = pct + "%";
}

async function generateReport() {
  const name = document.getElementById("name").value.trim();
  if (!name) { alert("Please enter the player's name."); return; }

  const btn = document.getElementById("generateBtn");
  btn.disabled = true;
  btn.textContent = "⏳ Generating report…";
  setProgress(10);
  showStatus("Claude is writing the report — usually takes 15–20 seconds…", "loading");

  const GRADES = {1:"Needs Support",2:"Developing",3:"Good",4:"Very Good",5:"Excellent"};
  let ratingsText = "";
  CORNERS.forEach(c => {
    ratingsText += `\n${c.label.toUpperCase()}:\n`;
    c.items.forEach((item, i) => {
      const v = ratings[c.key][i];
      ratingsText += `  • ${item}: ${v ? `${v} – ${GRADES[v]}` : "Not rated"}\n`;
    });
  });

  const noteComment  = document.getElementById("note_comment").value.trim();
  const noteStrength = document.getElementById("note_strengths").value.trim();
  const noteDevelop  = document.getElementById("note_develop").value.trim();

  const payload = {
    name, position: document.getElementById("position").value.trim(),
    coach: document.getElementById("coach").value.trim(),
    team:  document.getElementById("team").value.trim(),
    season: document.getElementById("season").value,
    ratingsText, noteComment, noteStrength, noteDevelop,
  };

  try {
    setProgress(30);
    const res = await fetch("/generate", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify(payload),
    });
    setProgress(80);
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.error || "Server error");
    }
    const blob = await res.blob();
    setProgress(100);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${name.replace(/ /g,"_")}_Player_Review.pdf`;
    a.click();
    showStatus("✅ PDF downloaded successfully!", "success");
  } catch(e) {
    showStatus("❌ Error: " + e.message, "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "⚡ Generate Report & Download PDF";
  }
}

buildCorners();
</script>
</body>
</html>"""

# ── PDF BUILDER ───────────────────────────────────────────────────────────────
def build_pdf(data, output_path):
    doc = SimpleDocTemplate(output_path, pagesize=A4,
        leftMargin=12*mm, rightMargin=12*mm, topMargin=10*mm, bottomMargin=12*mm)
    W = 186*mm

    def sty(name, **kw):
        return ParagraphStyle(name, **kw)

    styles = {
        "title":    sty("t", fontName="Helvetica-Bold", fontSize=20, textColor=colors.white, alignment=TA_CENTER),
        "subtitle": sty("s", fontName="Helvetica", fontSize=9, textColor=colors.HexColor("#7ab88a"), alignment=TA_CENTER, leading=13),
        "pl":       sty("pl", fontName="Helvetica-Bold", fontSize=8, textColor=MID_GREY, leading=10),
        "pv":       sty("pv", fontName="Helvetica-Bold", fontSize=13, textColor=DARK_GREY, leading=16),
        "sec":      sty("sec", fontName="Helvetica-Bold", fontSize=8, textColor=MID_GREY, spaceAfter=3, leading=10),
        "body":     sty("b", fontName="Helvetica", fontSize=9.5, textColor=DARK_GREY, leading=15, spaceAfter=4),
        "ri":       sty("ri", fontName="Helvetica", fontSize=9, textColor=DARK_GREY, leading=13),
        "ov_body":  sty("ob", fontName="Helvetica", fontSize=10, textColor=colors.white, leading=16),
        "bl":       sty("bl", fontName="Helvetica-Bold", fontSize=8.5, textColor=MID_GREY, spaceAfter=2, leading=11),
        "gk":       sty("gk", fontName="Helvetica", fontSize=8, textColor=MID_GREY, leading=11),
    }

    story = []

    # Header
    hdr = Table([[
        Paragraph("⚽", sty("cr", fontName="Helvetica-Bold", fontSize=28, textColor=colors.white, alignment=TA_CENTER)),
        [Paragraph("PLAYER REVIEW", styles["title"]),
         Paragraph("FA Four Corner Model  ·  " + data["team"], styles["subtitle"])],
        Paragraph("", styles["title"]),
    ]], colWidths=[18*mm, 150*mm, 18*mm])
    hdr.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),DARK_GREEN),
        ("TOPPADDING",(0,0),(-1,-1),10),("BOTTOMPADDING",(0,0),(-1,-1),10),
        ("LEFTPADDING",(0,0),(-1,-1),6),("RIGHTPADDING",(0,0),(-1,-1),6),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("LINEBELOW",(0,0),(-1,-1),2,LIGHT_GREEN),
    ]))
    story += [hdr, Spacer(1,4*mm)]

    # Player info
    def ic(lbl, val):
        return [Paragraph(lbl, styles["pl"]), Paragraph(val or "–", styles["pv"])]
    info = Table([[ic("PLAYER",data["name"]), ic("POSITION",data["position"]),
                   ic("COACH",data["coach"]), ic("REVIEW",data["season"])]],
                 colWidths=[W/4]*4)
    info.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),OFF_WHITE),("BOX",(0,0),(-1,-1),.5,RULE_GREY),
        ("LINEAFTER",(0,0),(-2,-1),.5,RULE_GREY),
        ("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8),
        ("LEFTPADDING",(0,0),(-1,-1),10),("RIGHTPADDING",(0,0),(-1,-1),8),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
    ]))
    story += [info, Spacer(1,4*mm)]

    # Grade key
    gk_text = "  ".join([f"<b>{k}</b> = {v}" for k,v in GRADE_LABELS.items()])
    gk = Table([[Paragraph("GRADE KEY:  " + gk_text, styles["gk"])]], colWidths=[W])
    gk.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),OFF_WHITE),("BOX",(0,0),(-1,-1),.5,RULE_GREY),
        ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
        ("LEFTPADDING",(0,0),(-1,-1),10),
    ]))
    story += [gk, Spacer(1,4*mm)]

    # Corner sections
    for key, title, icon, col, bg in CORNERS_DEF:
        items_scores = data["corners"][key]["items"]
        strengths    = data["corners"][key]["strengths"]
        develop      = data["corners"][key]["develop"]
        avg = sum(s for _,s in items_scores)/len(items_scores)

        elems = []
        hdr_tbl = Table([[
            Paragraph(f"{icon}  {title}", sty("ch", fontName="Helvetica-Bold", fontSize=13, textColor=colors.white, leading=16)),
            Paragraph(f"<b>{avg:.1f}</b>", sty("ca", fontName="Helvetica-Bold", fontSize=22, textColor=colors.white, alignment=TA_RIGHT, leading=26)),
        ]], colWidths=[130*mm, 30*mm])
        hdr_tbl.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,-1),col),
            ("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8),
            ("LEFTPADDING",(0,0),(-1,-1),10),("RIGHTPADDING",(0,0),(-1,-1),10),
            ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ]))
        elems.append(hdr_tbl)

        rows = []
        for item, score in items_scores:
            label = GRADE_LABELS.get(score,"")
            col_hex = col.hexval() if hasattr(col,"hexval") else "#333"
            dots_on  = f'<font color="{col_hex}">{"●"*score}</font>'
            dots_off = f'<font color="#cccccc">{"●"*(5-score)}</font>'
            rows.append([
                Paragraph(f"• {item}", styles["ri"]),
                Paragraph(dots_on + dots_off, sty("d", fontName="Helvetica", fontSize=10, leading=13)),
                Paragraph(f'<b>{score}</b> <font color="#888">{label}</font>',
                    sty("sc", fontName="Helvetica", fontSize=8.5, leading=13, alignment=TA_RIGHT)),
            ])
        rt = Table(rows, colWidths=[90*mm, 40*mm, 30*mm])
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
        ]], colWidths=[82*mm, 82*mm])
        txt.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,-1),colors.white),
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

    # Overall
    ov = Table([[
        [Paragraph("OVERALL COACH COMMENT", sty("ovh", fontName="Helvetica-Bold", fontSize=10, textColor=GOLD, leading=14, spaceAfter=6)),
         Paragraph(data["overall"], styles["ov_body"])]
    ]], colWidths=[W])
    ov.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),DARK_GREEN),("BOX",(0,0),(-1,-1),1,MID_GREEN),
        ("TOPPADDING",(0,0),(-1,-1),12),("BOTTOMPADDING",(0,0),(-1,-1),12),
        ("LEFTPADDING",(0,0),(-1,-1),14),("RIGHTPADDING",(0,0),(-1,-1),14),
        ("VALIGN",(0,0),(-1,-1),"TOP"),
    ]))
    story += [ov, Spacer(1,5*mm)]

    # Blank sections
    def blank(lbl):
        elems = []
        if lbl:
            elems.append(Paragraph(lbl, styles["bl"]))
        elems.append(Table([[Paragraph("",styles["body"])]], colWidths=[W], rowHeights=[14*mm],
            style=[("BOX",(0,0),(-1,-1),.5,RULE_GREY),("BACKGROUND",(0,0),(-1,-1),OFF_WHITE)]))
        elems.append(Spacer(1,3*mm))
        return elems

    story.append(Paragraph("PLAYER REFLECTIONS", sty("prh", fontName="Helvetica-Bold", fontSize=10, textColor=MID_GREY, leading=13, spaceAfter=4)))
    story += blank("What I've improved this season:")
    story += blank("What I want to get better at next:")
    story += blank("My goals for next term / season:")
    story.append(Paragraph("PARENT / GUARDIAN COMMENTS", sty("pgh", fontName="Helvetica-Bold", fontSize=10, textColor=MID_GREY, leading=13, spaceAfter=4)))
    story += blank("")

    doc.build(story)


# ── ROUTES ────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/generate", methods=["POST"])
def generate():
    body = request.get_json()
    name     = body.get("name","Player")
    position = body.get("position","")
    coach    = body.get("coach","")
    team     = body.get("team","")
    season   = body.get("season","Mid Season Review")
    ratings_text = body.get("ratingsText","")
    note_comment  = body.get("noteComment","")
    note_strength = body.get("noteStrength","")
    note_develop  = body.get("noteDevelop","")

    # Build prompt
    prompt = f"""Write a formal FA Four Corner Model player review for:
Player: {name} | Position: {position} | Coach: {coach} | Team: {team} | Review: {season}

RATINGS (1=Needs Support, 2=Developing, 3=Good, 4=Very Good, 5=Excellent):
{ratings_text}
{f"Coach comment: {note_comment}" if note_comment else ""}
{f"Key strengths: {note_strength}" if note_strength else ""}
{f"Development focus: {note_develop}" if note_develop else ""}

Return ONLY a JSON object in this exact format, no other text:
{{
  "technical_strengths": "...",
  "technical_develop": "...",
  "physical_strengths": "...",
  "physical_develop": "...",
  "psychological_strengths": "...",
  "psychological_develop": "...",
  "social_strengths": "...",
  "social_develop": "...",
  "overall": "..."
}}

Rules:
- Use {name}'s first name throughout
- Warm, professional, age-appropriate tone for U12 football
- Praise scores of 4-5, encourage development for scores of 1-2
- Each strengths/develop paragraph: 2-4 sentences
- Overall: 3-4 sentences summarising the season
"""

    api_key = os.environ.get("ANTHROPIC_API_KEY","")
    if not api_key:
        return jsonify({"error": "ANTHROPIC_API_KEY not set on server"}), 500

    try:
        client = anthropic.Anthropic(api_key=api_key, timeout=60.0)
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            messages=[{"role":"user","content": prompt}]
        )
        raw = message.content[0].text.strip()
        # Strip markdown code fences if present
        raw = re.sub(r"^```json\s*","", raw)
        raw = re.sub(r"\s*```$","", raw)
        ai = json.loads(raw)
    except json.JSONDecodeError as e:
        return jsonify({"error": f"AI response parse error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # Parse ratings from text
    def parse_scores(corner_key):
        items = CORNER_ITEMS[corner_key]
        scores = []
        for item in items:
            pattern = re.compile(re.escape(f"• {item}") + r":\s*(\d)", re.IGNORECASE)
            m = pattern.search(ratings_text)
            score = int(m.group(1)) if m else 3
            scores.append((item, score))
        return scores

    data = {
        "name": name, "position": position, "coach": coach,
        "team": team, "season": season,
        "overall": ai.get("overall",""),
        "corners": {
            "technical":     {"items": parse_scores("technical"),     "strengths": ai.get("technical_strengths",""),     "develop": ai.get("technical_develop","")},
            "physical":      {"items": parse_scores("physical"),      "strengths": ai.get("physical_strengths",""),      "develop": ai.get("physical_develop","")},
            "psychological": {"items": parse_scores("psychological"), "strengths": ai.get("psychological_strengths",""), "develop": ai.get("psychological_develop","")},
            "social":        {"items": parse_scores("social"),        "strengths": ai.get("social_strengths",""),        "develop": ai.get("social_develop","")},
        }
    }

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        pdf_path = f.name

    build_pdf(data, pdf_path)

    return send_file(pdf_path, as_attachment=True,
                     download_name=f"{name.replace(' ','_')}_Player_Review.pdf",
                     mimetype="application/pdf")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
