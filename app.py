import os
import json
import anthropic
from flask import Flask, request, jsonify, send_file, Response
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, Image as RLImage
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
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

# Foundation phase colours
DEV_COL   = colors.HexColor("#1565C0")
SEC_COL   = colors.HexColor("#F9A825")
EXC_COL   = colors.HexColor("#2E7D32")

GRADE_LABELS = {1:"Needs Support",2:"Developing",3:"Good",4:"Very Good",5:"Excellent"}
FOUNDATION_LABELS = {"D":"Developing","S":"Secure","E":"Excelling"}

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

# Age groups split by system
FOUNDATION_AGES = ["U7","U8","U9","U10","U11"]
STANDARD_AGES   = ["U12","U13","U14","U15","U16"]

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FCYFC Player Review Tool</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,sans-serif;background:#f9f7f2;min-height:100vh;color:#111}
header{background:#1a1a1a;padding:14px 20px;display:flex;align-items:center;gap:14px;position:sticky;top:0;z-index:100;border-bottom:3px solid #F5A800}
header img{width:48px;height:48px;border-radius:50%;object-fit:cover}
header h1{color:white;font-size:17px;font-weight:800}
header p{color:#F5A800;font-size:10px;letter-spacing:1.5px;margin-top:2px;text-transform:uppercase}
.wrap{max-width:700px;margin:0 auto;padding:20px 14px}
.card{background:white;border-radius:10px;border:1px solid #e8e0d0;box-shadow:0 1px 5px rgba(0,0,0,.06);margin-bottom:16px}
.card-head{padding:13px 18px;border-bottom:1px solid #f0ebe0;font-weight:800;font-size:12px;text-transform:uppercase;letter-spacing:1px;color:#1a1a1a}
.card-body{padding:14px 18px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:12px}
label{display:block;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#666;margin-bottom:5px}
input,select,textarea{width:100%;padding:9px 11px;border:1.5px solid #ddd;border-radius:6px;font-size:14px;color:#111;background:#fafaf8;font-family:inherit}
textarea{resize:vertical;line-height:1.6}
.corner-header{display:flex;align-items:center;gap:10px;padding:13px 18px;border-radius:10px 10px 0 0}
.corner-title{font-weight:800;font-size:15px;color:#111;flex:1}
.rating-row{display:flex;align-items:center;justify-content:space-between;padding:9px 0;border-bottom:1px solid #f5f0e8;gap:10px}
.rating-row:last-child{border-bottom:none}
.rating-label{font-size:13px;color:#222;flex:1}

/* Standard 1-5 stars */
.stars{display:flex;gap:5px;flex-shrink:0}
.star{width:32px;height:32px;border:2px solid #ddd;border-radius:6px;background:white;color:#aaa;font-weight:700;font-size:13px;cursor:pointer;transition:all .1s;display:flex;align-items:center;justify-content:center}

/* Foundation phase buttons */
.foundation-btns{display:flex;gap:6px;flex-shrink:0}
.fbtn{padding:6px 12px;border:2px solid #ddd;border-radius:20px;background:white;font-size:12px;font-weight:700;cursor:pointer;transition:all .15s;white-space:nowrap;color:#666}
.fbtn.dev.active{background:#1565C0;border-color:#1565C0;color:white}
.fbtn.sec.active{background:#F9A825;border-color:#F9A825;color:#1a1a1a}
.fbtn.exc.active{background:#2E7D32;border-color:#2E7D32;color:white}
.fbtn.dev:hover{border-color:#1565C0;color:#1565C0}
.fbtn.sec:hover{border-color:#F9A825;color:#9a6a00}
.fbtn.exc:hover{border-color:#2E7D32;color:#2E7D32}

/* Legend */
.legend{background:white;border-radius:8px;border:1px solid #e8e0d0;padding:10px 18px;margin-bottom:16px;display:flex;gap:16px;flex-wrap:wrap;align-items:center;font-size:12px;color:#555}
.legend-dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:4px}

.btn{width:100%;padding:16px;border:none;border-radius:9px;font-size:16px;font-weight:800;cursor:pointer;letter-spacing:.5px;transition:all .2s;margin-bottom:8px}
.btn-gold{background:#F5A800;color:#1a1a1a}
.btn-gold:hover{background:#FFC93C}
.btn-gold:disabled{background:#ccc;cursor:not-allowed;color:#888}
.btn-green{background:#1e7a35;color:white}
.btn-green:hover{background:#2d8a47}
.btn-outline{background:white;color:#555;border:1.5px solid #ccc}
.status{margin-top:12px;padding:12px 16px;border-radius:8px;font-size:14px;display:none;text-align:center}
.status.loading{background:#fff8e6;color:#9a6a00;display:block;border:1px solid #F5A800}
.status.error{background:#fde8e8;color:#b52200;display:block}
.status.success{background:#e8f5ec;color:#1e7a35;display:block}

/* Foundation banner */
.foundation-banner{background:#e8f0fe;border:1px solid #1565C0;border-radius:8px;padding:12px 16px;margin-bottom:16px;font-size:13px;color:#1565C0;font-weight:600}

#editScreen{display:none}
.edit-section{background:white;border-radius:10px;border:1px solid #e8e0d0;margin-bottom:16px;overflow:hidden}
.edit-section-header{padding:12px 18px;font-weight:800;font-size:13px;color:white}
.edit-section-body{padding:14px 18px}
.edit-field{margin-bottom:14px}
.edit-field label{display:block;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#666;margin-bottom:5px}
.edit-field textarea{width:100%;padding:10px 12px;border:1.5px solid #ddd;border-radius:6px;font-size:14px;color:#111;background:#fafaf8;resize:vertical;line-height:1.6;font-family:inherit;min-height:80px}
.edit-field textarea:focus{outline:none;border-color:#F5A800}
.edit-banner{background:#fff8e6;border:1px solid #F5A800;border-radius:8px;padding:14px 18px;margin-bottom:16px;font-size:14px;color:#7a5a00;line-height:1.6}
</style>
</head>
<body>
<header>
  <img src="/logo" alt="FCYFC">
  <div>
    <h1>Falmouth Community Youth FC</h1>
    <p>Player Review Tool - FA Four Corner Model</p>
  </div>
</header>
<div class="wrap">

<!-- FORM SCREEN -->
<div id="formScreen">
  <div class="card">
    <div class="card-head">Player Details</div>
    <div class="card-body">
      <div class="grid2">
        <div><label>Player Name</label><input id="name" placeholder="e.g. Declan Rice"></div>
        <div><label>Position</label><input id="position" placeholder="e.g. Midfielder"></div>
        <div><label>Coach</label><input id="coach" placeholder="e.g. Arteta"></div>
        <div><label>Team</label><input id="team" placeholder="e.g. U12 Ravens"></div>
      </div>
      <div class="grid2" style="margin-top:12px">
        <div>
          <label>Age Group</label>
          <select id="agegroup" onchange="onAgeChange()">
            <option>U7</option><option>U8</option><option>U9</option>
            <option>U10</option><option>U11</option>
            <option selected>U12</option>
            <option>U13</option><option>U14</option><option>U15</option><option>U16</option>
          </select>
        </div>
        <div>
          <label>Review Period</label>
          <select id="season">
            <option>Mid Season Review</option><option>End of Season Review</option>
            <option>Pre-Season Review</option><option>Quarterly Review</option>
          </select>
        </div>
      </div>
    </div>
  </div>

  <!-- Legend - swaps based on age group -->
  <div class="legend" id="legend-standard">
    <strong>Grade:</strong>
    <span><strong>1</strong> Needs Support</span>
    <span><strong>2</strong> Developing</span>
    <span><strong>3</strong> Good</span>
    <span><strong>4</strong> Very Good</span>
    <span><strong>5</strong> Excellent</span>
  </div>
  <div class="legend" id="legend-foundation" style="display:none">
    <strong>Grade:</strong>
    <span><span class="legend-dot" style="background:#1565C0"></span>Developing</span>
    <span><span class="legend-dot" style="background:#F9A825"></span>Secure</span>
    <span><span class="legend-dot" style="background:#2E7D32"></span>Excelling</span>
  </div>

  <div id="corners"></div>

  <div class="card">
    <div class="card-head">Coach Notes <span style="color:#aaa;font-weight:400;text-transform:none;letter-spacing:0">(optional)</span></div>
    <div class="card-body">
      <div style="margin-bottom:12px"><label>Overall Comment</label><textarea id="note_comment" rows="2" placeholder="e.g. A really positive season so far..."></textarea></div>
      <div class="grid2">
        <div><label>Key Strengths</label><textarea id="note_strengths" rows="2" placeholder="e.g. Brilliant attitude and effort..."></textarea></div>
        <div><label>Development Focus</label><textarea id="note_develop" rows="2" placeholder="e.g. Continue working on first touch..."></textarea></div>
      </div>
    </div>
  </div>

  <button class="btn btn-gold" id="generateBtn" onclick="generateReport()">Generate Report</button>
  <div class="status" id="status"></div>
</div>

<!-- EDIT SCREEN -->
<div id="editScreen">
  <div class="edit-banner">
    Review and edit the text below. Change anything you like before downloading the PDF.
  </div>
  <div class="edit-section">
    <div class="edit-section-header" style="background:#1e7a35">Technical / Tactical</div>
    <div class="edit-section-body">
      <div class="edit-field"><label>Strengths</label><textarea id="e_technical_strengths" rows="4"></textarea></div>
      <div class="edit-field"><label>Areas to Develop</label><textarea id="e_technical_develop" rows="3"></textarea></div>
    </div>
  </div>
  <div class="edit-section">
    <div class="edit-section-header" style="background:#9a6a00">Physical</div>
    <div class="edit-section-body">
      <div class="edit-field"><label>Strengths</label><textarea id="e_physical_strengths" rows="4"></textarea></div>
      <div class="edit-field"><label>Areas to Develop</label><textarea id="e_physical_develop" rows="3"></textarea></div>
    </div>
  </div>
  <div class="edit-section">
    <div class="edit-section-header" style="background:#2255cc">Psychological</div>
    <div class="edit-section-body">
      <div class="edit-field"><label>Strengths</label><textarea id="e_psychological_strengths" rows="4"></textarea></div>
      <div class="edit-field"><label>Areas to Develop</label><textarea id="e_psychological_develop" rows="3"></textarea></div>
    </div>
  </div>
  <div class="edit-section">
    <div class="edit-section-header" style="background:#b52200">Social</div>
    <div class="edit-section-body">
      <div class="edit-field"><label>Strengths</label><textarea id="e_social_strengths" rows="4"></textarea></div>
      <div class="edit-field"><label>Areas to Develop</label><textarea id="e_social_develop" rows="3"></textarea></div>
    </div>
  </div>
  <div class="edit-section">
    <div class="edit-section-header" style="background:#1a1a1a">Overall Coach Comment</div>
    <div class="edit-section-body">
      <div class="edit-field"><textarea id="e_overall" rows="5"></textarea></div>
    </div>
  </div>
  <button class="btn btn-green" onclick="downloadPDF()">Download PDF</button>
  <button class="btn btn-outline" onclick="goBack()">Back to Form</button>
  <div class="status" id="status2"></div>
</div>

</div>
<script>
const FOUNDATION_AGES = ["U7","U8","U9","U10","U11"];
const CORNERS=[
  {key:"technical",label:"Technical / Tactical",color:"#1e7a35",bg:"#f0f9f3",
   items:["First touch and ball control","Dribbling and ball manipulation","Passing accuracy and weight","Scanning before receiving","Decision-making in possession","Retaining possession under pressure","Defensive positioning and body shape","Understanding transitions","Position-specific responsibilities"]},
  {key:"physical",label:"Physical",color:"#9a6a00",bg:"#fdf8ec",
   items:["Agility and coordination","Acceleration and speed","Strength in duels","Balance and stability","Endurance and work rate","Movement efficiency","Position-specific physical demands"]},
  {key:"psychological",label:"Psychological",color:"#2255cc",bg:"#f0f4ff",
   items:["Focus and concentration","Resilience after mistakes","Confidence in possession","Willingness to take responsibility","Game understanding and anticipation","Leadership behaviours","Motivation and attitude","Consistency across training and matches"]},
  {key:"social",label:"Social",color:"#b52200",bg:"#fff4f1",
   items:["Communication with teammates","Calling for the ball with purpose","Supporting and organising others","Respect for coaches, referees, teammates","Teamwork and cooperation","Contribution to team environment","Ability to work in groups"]},
];

const ratings={};
CORNERS.forEach(c=>{ratings[c.key]={};c.items.forEach((_,i)=>ratings[c.key][i]=null);});
let currentPayload=null;
let isFoundation=false;

function isFoundationAge(){
  return FOUNDATION_AGES.includes(document.getElementById("agegroup").value);
}

function onAgeChange(){
  const foundation = isFoundationAge();
  isFoundation = foundation;
  document.getElementById("legend-standard").style.display = foundation?"none":"flex";
  document.getElementById("legend-foundation").style.display = foundation?"flex":"none";
  // Reset all ratings
  CORNERS.forEach(c=>c.items.forEach((_,i)=>ratings[c.key][i]=null));
  // Rebuild corner rating rows
  buildCorners();
}

function buildCorners(){
  var wrap=document.getElementById("corners");
  wrap.innerHTML="";
  var foundation = isFoundationAge();
  CORNERS.forEach(function(c){
    var rows="";
    c.items.forEach(function(item,i){
      if(foundation){
        rows+='<div class="rating-row">';
        rows+='<span class="rating-label">'+item+'</span>';
        rows+='<div class="foundation-btns">';
        rows+='<button class="fbtn dev" onclick="rateF(''+c.key+'','+i+','D')" id="fb_'+c.key+'_'+i+'_D">Developing</button>';
        rows+='<button class="fbtn sec" onclick="rateF(''+c.key+'','+i+','S')" id="fb_'+c.key+'_'+i+'_S">Secure</button>';
        rows+='<button class="fbtn exc" onclick="rateF(''+c.key+'','+i+','E')" id="fb_'+c.key+'_'+i+'_E">Excelling</button>';
        rows+='</div></div>';
      } else {
        rows+='<div class="rating-row">';
        rows+='<span class="rating-label">'+item+'</span>';
        rows+='<div class="stars" id="stars_'+c.key+'_'+i+'">';
        [1,2,3,4,5].forEach(function(n){
          rows+='<div class="star" onclick="rate(''+c.key+'','+i+','+n+')" onmouseenter="hov(''+c.key+'','+i+','+n+',true)" onmouseleave="hov(''+c.key+'','+i+','+n+',false)">'+n+'</div>';
        });
        rows+='</div></div>';
      }
    });
    var html='<div class="corner-header" style="background:'+c.bg+';border-bottom:2px solid '+c.color+'25;border-radius:10px 10px 0 0">';
    html+='<span class="corner-title">'+c.label+'</span></div>';
    html+='<div class="card-body">'+rows+'</div>';
    var div=document.createElement("div");
    div.className="card";
    div.style.marginBottom="16px";
    div.innerHTML=html;
    wrap.appendChild(div);
  });
}

function rateF(key,idx,val){
  ratings[key][idx] = ratings[key][idx]===val ? null : val;
  ["D","S","E"].forEach(v=>{
    const btn=document.getElementById("fb_"+key+"_"+idx+"_"+v);
    if(btn){
      btn.classList.remove("active");
      if(ratings[key][idx]===v) btn.classList.add("active");
    }
  });
}

function rate(key,idx,val){
  ratings[key][idx]=ratings[key][idx]===val?null:val;
  renderStars(key,idx,ratings[key][idx]);
}
function hov(key,idx,val,on){
  const cur=ratings[key][idx]||0;
  const c=CORNERS.find(x=>x.key===key);
  document.querySelectorAll("#stars_"+key+"_"+idx+" .star").forEach((s,i)=>{
    const a=i<(on?val:cur);
    s.style.borderColor=a?c.color:"#ddd";
    s.style.background=a?c.color:"white";
    s.style.color=a?"white":"#aaa";
  });
}
function renderStars(key,idx,val){
  const c=CORNERS.find(x=>x.key===key);
  document.querySelectorAll("#stars_"+key+"_"+idx+" .star").forEach((s,i)=>{
    const a=val&&i<val;
    s.style.borderColor=a?c.color:"#ddd";
    s.style.background=a?c.color:"white";
    s.style.color=a?"white":"#aaa";
  });
}

function showStatus(id,msg,type){const el=document.getElementById(id);el.textContent=msg;el.className="status "+type;}

function buildRatingsText(){
  const GRADES={1:"Needs Support",2:"Developing",3:"Good",4:"Very Good",5:"Excellent"};
  const FLABELS={D:"Developing",S:"Secure",E:"Excelling"};
  const foundation=isFoundationAge();
  let txt="";
  CORNERS.forEach(c=>{
    txt+="\n"+c.label.toUpperCase()+":\n";
    c.items.forEach((item,i)=>{
      const v=ratings[c.key][i];
      if(foundation){
        txt+="  * "+item+": "+(v?FLABELS[v]:"Not rated")+"\n";
      } else {
        txt+="  * "+item+": "+(v?v+" - "+GRADES[v]:"Not rated")+"\n";
      }
    });
  });
  return txt;
}

async function generateReport(){
  const name=document.getElementById("name").value.trim();
  if(!name){alert("Please enter the player's name.");return;}
  const btn=document.getElementById("generateBtn");
  btn.disabled=true;btn.textContent="Generating report...";
  showStatus("status","Generating report - please wait...","loading");

  currentPayload={
    name,
    position:document.getElementById("position").value.trim(),
    coach:document.getElementById("coach").value.trim(),
    team:document.getElementById("team").value.trim(),
    season:document.getElementById("season").value,
    agegroup:document.getElementById("agegroup").value,
    isFoundation:isFoundationAge(),
    ratingsText:buildRatingsText(),
    noteComment:document.getElementById("note_comment").value.trim(),
    noteStrength:document.getElementById("note_strengths").value.trim(),
    noteDevelop:document.getElementById("note_develop").value.trim(),
  };

  try{
    const res=await fetch("/generate_text",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(currentPayload)});
    if(!res.ok){const err=await res.json();throw new Error(err.error||"Server error");}
    const ai=await res.json();
    document.getElementById("e_technical_strengths").value=ai.technical_strengths||"";
    document.getElementById("e_technical_develop").value=ai.technical_develop||"";
    document.getElementById("e_physical_strengths").value=ai.physical_strengths||"";
    document.getElementById("e_physical_develop").value=ai.physical_develop||"";
    document.getElementById("e_psychological_strengths").value=ai.psychological_strengths||"";
    document.getElementById("e_psychological_develop").value=ai.psychological_develop||"";
    document.getElementById("e_social_strengths").value=ai.social_strengths||"";
    document.getElementById("e_social_develop").value=ai.social_develop||"";
    document.getElementById("e_overall").value=ai.overall||"";
    document.getElementById("formScreen").style.display="none";
    document.getElementById("editScreen").style.display="block";
    window.scrollTo(0,0);
  }catch(e){showStatus("status","Error: "+e.message,"error");}
  finally{btn.disabled=false;btn.textContent="Generate Report";}
}

async function downloadPDF(){
  showStatus("status2","Generating your PDF...","loading");
  const btn=event.target;btn.disabled=true;
  const editedText={
    technical_strengths:document.getElementById("e_technical_strengths").value,
    technical_develop:document.getElementById("e_technical_develop").value,
    physical_strengths:document.getElementById("e_physical_strengths").value,
    physical_develop:document.getElementById("e_physical_develop").value,
    psychological_strengths:document.getElementById("e_psychological_strengths").value,
    psychological_develop:document.getElementById("e_psychological_develop").value,
    social_strengths:document.getElementById("e_social_strengths").value,
    social_develop:document.getElementById("e_social_develop").value,
    overall:document.getElementById("e_overall").value,
  };
  try{
    const res=await fetch("/generate_pdf",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({...currentPayload,...editedText})});
    if(!res.ok){const err=await res.json();throw new Error(err.error||"Server error");}
    const blob=await res.blob();
    const url=URL.createObjectURL(blob);
    const a=document.createElement("a");a.href=url;
    a.download=currentPayload.name.replace(/ /g,"_")+"_Player_Review.pdf";a.click();
    showStatus("status2","PDF downloaded successfully!","success");
  }catch(e){showStatus("status2","Error: "+e.message,"error");}
  finally{btn.disabled=false;}
}

function goBack(){
  document.getElementById("editScreen").style.display="none";
  document.getElementById("formScreen").style.display="block";
  window.scrollTo(0,0);
}

window.onload = function(){ onAgeChange(); };
</script>
</body>
</html>"""


@app.route("/logo")
def serve_logo():
    logo_path = os.path.join(os.path.dirname(__file__), "logo.png")
    if os.path.exists(logo_path):
        return send_file(logo_path, mimetype="image/png")
    return "", 404


def build_pdf(data, output_path):
    doc = SimpleDocTemplate(output_path, pagesize=A4,
        leftMargin=12*mm, rightMargin=12*mm, topMargin=10*mm, bottomMargin=12*mm)
    W = 186*mm
    foundation = data.get("isFoundation", False)

    def sty(name, **kw):
        return ParagraphStyle(name, **kw)

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
    logo_path = os.path.join(os.path.dirname(__file__), "logo.png")
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

    # Player info strip
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
        gk_text = "  Developing     Secure     Excelling"
        gk_row = [[
            Paragraph("GRADE KEY:", styles["gk"]),
            Paragraph("Developing", sty("gd", fontName="Helvetica-Bold", fontSize=8, textColor=DEV_COL, leading=11)),
            Paragraph("Secure", sty("gs", fontName="Helvetica-Bold", fontSize=8, textColor=SEC_COL, leading=11)),
            Paragraph("Excelling", sty("ge", fontName="Helvetica-Bold", fontSize=8, textColor=EXC_COL, leading=11)),
        ]]
        gk = Table(gk_row, colWidths=[30*mm, 50*mm, 50*mm, 56*mm])
    else:
        gk_text = "  ".join(["%d = %s" % (k,v) for k,v in GRADE_LABELS.items()])
        gk_row = [[Paragraph("GRADE KEY:  " + gk_text, styles["gk"])]]
        gk = Table(gk_row, colWidths=[W])
    gk.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),OFF_WHITE),("BOX",(0,0),(-1,-1),.5,RULE_GREY),
        ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
        ("LEFTPADDING",(0,0),(-1,-1),10),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
    ]))
    story += [gk, Spacer(1,4*mm)]

    # Corner sections
    for key, title, col, bg in CORNERS_DEF:
        items_scores = data["corners"][key]["items"]
        strengths    = data["corners"][key]["strengths"]
        develop      = data["corners"][key]["develop"]
        elems = []

        # Header bar (no avg for foundation)
        if foundation:
            hdr_content = [[
                Paragraph(title, sty("ch", fontName="Helvetica-Bold", fontSize=13, textColor=WHITE, leading=16)),
            ]]
            hdr_widths = [W]
        else:
            scores_only = [s for _,s in items_scores if isinstance(s,int)]
            avg = sum(scores_only)/len(scores_only) if scores_only else 0
            hdr_content = [[
                Paragraph(title, sty("ch", fontName="Helvetica-Bold", fontSize=13, textColor=WHITE, leading=16)),
                Paragraph("<b>%.1f</b>" % avg, sty("ca", fontName="Helvetica-Bold", fontSize=22, textColor=WHITE, alignment=TA_RIGHT, leading=26)),
            ]]
            hdr_widths = [130*mm, 30*mm]

        hdr_tbl = Table(hdr_content, colWidths=hdr_widths)
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
                # Coloured badge for foundation
                if score == "D":
                    badge = Paragraph("<b>Developing</b>", sty("fb", fontName="Helvetica-Bold", fontSize=9, textColor=DEV_COL, leading=13))
                elif score == "S":
                    badge = Paragraph("<b>Secure</b>", sty("fb", fontName="Helvetica-Bold", fontSize=9, textColor=SEC_COL, leading=13))
                elif score == "E":
                    badge = Paragraph("<b>Excelling</b>", sty("fb", fontName="Helvetica-Bold", fontSize=9, textColor=EXC_COL, leading=13))
                else:
                    badge = Paragraph("-", styles["ri"])
                rows.append([
                    Paragraph("- %s" % item, styles["ri"]),
                    badge,
                ])
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

        col_widths = [100*mm, 60*mm] if foundation else [90*mm, 40*mm, 30*mm]
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
        "U7":  "Very young player (5-7). Use very simple, fun, celebratory language. Short sentences. Focus entirely on enjoyment, effort and trying hard. No tactical language.",
        "U8":  "Young player (7-8). Simple, fun, encouraging language. Celebrate effort and enjoyment. Keep it positive and easy to understand.",
        "U9":  "Player is 8-9. Warm encouraging language. Focus on fun, basic skills and effort. Avoid complex tactical terms.",
        "U10": "Player is 9-10. Encouraging language. Focus on developing skills and enjoyment. Simple development points.",
        "U11": "Player is 10-11. Clear encouraging language. Begin to introduce simple tactical ideas. Positive and supportive tone.",
        "U12": "Player is 11-12. Clear encouraging language with some tactical awareness. Balance praise with simple development points.",
        "U13": "Player is 12-13. More detailed tactical language. Honest constructive feedback alongside praise.",
        "U14": "Player is 13-14. Detailed tactical and technical language. Specific honest feedback alongside praise.",
        "U15": "Player is 14-15. Mature detailed tactical language. Specific technical and tactical development areas.",
        "U16": "Player is 15-16. Mature detailed tactical language. Specific technical and tactical development. Treat them as developing adults.",
    }

    if foundation:
        rating_system = "Ratings use: Developing / Secure / Excelling (no numbers). Reference these in your text."
    else:
        rating_system = "Ratings use 1-5 scale. Praise scores of 4-5 warmly. Encourage development on scores of 1-2."

    prompt = """Write a FA Four Corner Model player review for Falmouth Community Youth Football Club.
Player: %s | Position: %s | Coach: %s | Team: %s | Age Group: %s | Review: %s

AGE GUIDANCE: %s
RATING SYSTEM: %s

RATINGS:
%s
%s%s%s
Return ONLY valid JSON, no markdown:
{"technical_strengths":"...","technical_develop":"...","physical_strengths":"...","physical_develop":"...","psychological_strengths":"...","psychological_develop":"...","social_strengths":"...","social_develop":"...","overall":"..."}

Use %s's first name throughout. Match language and complexity carefully to the age group guidance.""" % (
        name, position, coach, team, agegroup, season,
        age_guidance.get(agegroup,""),
        rating_system,
        ratings_text,
        ("Coach comment: %s\n" % note_comment) if note_comment else "",
        ("Key strengths: %s\n" % note_strength) if note_strength else "",
        ("Development focus: %s\n" % note_develop) if note_develop else "",
        name
    )

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
    return Response(HTML, mimetype="text/html")


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
        name         = body.get("name","Player")
        ratings_text = body.get("ratingsText","")
        foundation   = body.get("isFoundation", False)
        FLABELS = {"Developing":"D","Secure":"S","Excelling":"E"}

        def parse_scores(corner_key):
            items = CORNER_ITEMS[corner_key]
            scores = []
            for item in items:
                pattern = re.compile(re.escape("* " + item) + r":\s*(.+)", re.IGNORECASE)
                m = pattern.search(ratings_text)
                if m:
                    val = m.group(1).strip()
                    if foundation:
                        # Map text label back to code
                        code = FLABELS.get(val, val[0] if val else "D")
                        scores.append((item, code))
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
