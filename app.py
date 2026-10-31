import streamlit as st
import sqlite3, datetime as dt, io, html
from pathlib import Path
from collections import Counter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, KeepTogether, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT=Path(__file__).resolve().parent
SUBJECTS=['Český jazyk – mluvnice', 'Český jazyk – čtení', 'Matematika – aritmetika', 'Matematika – geometrie', 'ČJS – Člověk a jeho svět', 'Informatika', 'Tělesná výchova', 'ČSP – Člověk a svět práce', 'UVČ – Užité výtvarné činnosti', 'Výtvarná výchova', 'SH – Sportovní hry', 'Hudební výchova']
CATALOG={
'Práce s učivem a zadáním':['Vysvětlení a zopakování zadání','Ověření porozumění úkolu','Rozdělení úkolu na menší kroky','Procvičování učiva','Podpora při čtení a porozumění textu','Podpora při psaní a grafomotorice','Pomoc při řešení úloh','Pomoc při práci s učebnicí a pracovním listem','Podpora při práci s digitální technikou','Podpora samostatného plnění úkolů','Kontrola postupu práce a zpětná vazba'],
'Pozornost, chování a sociální podpora':['Podpora soustředění a návratu k úkolu','Motivace a povzbuzení žáka','Zklidnění při emočním rozrušení','Podpora při zvládání neúspěchu','Pomoc při řešení konfliktu','Podpora komunikace mezi žáky','Podpora zapojení do kolektivu','Podpora dodržování pravidel','Doprovázení při náročné situaci'],
'Organizace výuky':['Příprava pracovních míst','Rozdávání a sběr materiálů','Organizace skupinové práce','Pomoc při střídání činností','Organizační podpora při praktických činnostech','Pomoc při práci na stanovištích','Technická podpora při výuce','Organizace třídních aktivit'],
'Příprava a zajištění materiálů':['Kopírování a tisk pracovních listů','Stříhání, laminování a kompletace materiálů','Výroba a úprava didaktických pomůcek','Příprava výtvarných a pracovních potřeb','Zajišťování pomůcek a materiálu po škole','Příprava diferencovaných zadání podle pokynů učitele','Příprava materiálů pro jednotlivé žáky','Uspořádání a ukládání pomůcek','Příprava techniky pro výuku'],
'Dohled, doprovod a praktická pomoc':['Doprovod žáků při přesunech po škole','Dohled o přestávce podle pověření','Doprovod na školní akci','Pomoc při organizaci exkurze nebo vycházky','Podpora bezpečného pohybu a orientace','Pomoc při sebeobslužných činnostech podle potřeb žáka','Pomoc při přípravě na tělesnou nebo pracovní výchovu','Doprovod žáka při individuálně řešené situaci'],
'Spolupráce s učitelem':['Konzultace průběhu výuky','Domluva na rozdělení úkolů v hodině','Předávání poznatků o práci žáků','Plánování podpory na další hodiny','Společné vyhodnocení účinnosti podpory','Příprava úprav úkolů a materiálů','Spolupráce při organizaci třídních aktivit','Konzultace s dalšími pedagogickými pracovníky'],
'Dokumentace a administrativa':['Vedení pracovního deníku asistentky','Záznam průběhu poskytované podpory','Příprava podkladů pro učitele','Třídění a evidence pracovních materiálů','Příprava podkladů pro pedagogickou konzultaci','Evidence a organizace didaktických pomůcek','Další související administrativní činnost'],
'Školní akce a mimořádné činnosti':['Organizační pomoc při školní akci','Příprava a úklid prostor po akci','Pomoc při projektovém dni','Podpora žáků během soutěže nebo vystoupení','Příprava výzdoby a prezentací žákovských prací','Pomoc při mimořádné změně organizace výuky','Jiná činnost podle pokynů učitele související s prací asistentky'],
'Profesní a metodické činnosti':['Účast na pracovní poradě','Metodická konzultace','Seznamování s výukovými postupy a materiály','Příprava na práci se žáky','Účast na odborném vzdělávání','Vyhodnocování vlastní práce a příprava dalších postupů']}
GENERAL=list(dict.fromkeys(a for group in CATALOG.values() for a in group))
FAVORITES=['Vysvětlení a zopakování zadání','Ověření porozumění úkolu','Rozdělení úkolu na menší kroky','Procvičování učiva','Podpora při čtení a porozumění textu','Pomoc při řešení úloh','Podpora soustředění a návratu k úkolu','Podpora samostatného plnění úkolů']
SAMPLE=['Postupné předání instrukcí','Ověření porozumění zadání','Rozdělení slovní úlohy na kroky','Vizuální opora v matematice','Použití kompenzační pomůcky','Podpora pozornosti a návratu k práci','Umožnění pohybové aktivity','Individuální procvičení učiva','Podpora samostatnosti']
LEVELS=['Krátká','Průběžná','Intenzivní']
DAYS=['Pondělí','Úterý','Středa','Čtvrtek','Pátek']

def connect():
 c=sqlite3.connect(':memory:', check_same_thread=False)
 c.execute('CREATE TABLE IF NOT EXISTS pupils (code TEXT PRIMARY KEY, procedures TEXT NOT NULL DEFAULT \'\')')
 c.execute('CREATE TABLE IF NOT EXISTS records (id INTEGER PRIMARY KEY AUTOINCREMENT, day TEXT NOT NULL, lesson INTEGER NOT NULL, subject TEXT NOT NULL, pupil TEXT NOT NULL, activity TEXT NOT NULL, coverage TEXT NOT NULL, note TEXT NOT NULL DEFAULT \'\')')
 c.execute('CREATE TABLE IF NOT EXISTS sessions (id INTEGER PRIMARY KEY AUTOINCREMENT, day TEXT NOT NULL, lesson INTEGER NOT NULL, subject TEXT NOT NULL, shared TEXT NOT NULL, coverage TEXT NOT NULL, note TEXT NOT NULL DEFAULT \'\')')
 c.execute('CREATE TABLE IF NOT EXISTS session_pupils (session_id INTEGER NOT NULL, pupil TEXT NOT NULL, intensity TEXT NOT NULL, activities TEXT NOT NULL DEFAULT \'\', PRIMARY KEY(session_id,pupil))')
 c.execute("CREATE TABLE IF NOT EXISTS session_groups (session_id INTEGER PRIMARY KEY, group_size INTEGER, members TEXT NOT NULL DEFAULT '')")
 c.execute('CREATE TABLE IF NOT EXISTS timetable (weekday INTEGER NOT NULL, lesson INTEGER NOT NULL, subject TEXT NOT NULL, PRIMARY KEY(weekday,lesson))')
 c.commit();return c

def fetch(c,start,end):
 rows=c.execute('SELECT id,day,lesson,subject,shared,coverage,note FROM sessions WHERE day BETWEEN ? AND ? ORDER BY day,lesson,id',(start,end)).fetchall()
 old=c.execute('SELECT day,lesson,subject,pupil,activity,coverage,note FROM records WHERE day BETWEEN ? AND ? ORDER BY day,lesson',(start,end)).fetchall()
 return rows,old

def group_info(c,sid):
 r=c.execute('SELECT group_size,members FROM session_groups WHERE session_id=?',(sid,)).fetchone()
 return r if r else (None,'')

def details(c,sid):
 return c.execute('SELECT pupil,intensity,activities FROM session_pupils WHERE session_id=? ORDER BY pupil',(sid,)).fetchall()

def summarize(c, rows):
 actions=Counter()
 for sid,day,lesson,subject,shared,coverage,note in rows:
  for action in shared.split('; '):
   if action.strip(): actions[action.strip()]+=1
  for code,level,acts in details(c,sid):
   for action in acts.split('; '):
    if action.strip(): actions[action.strip()]+=1
 return actions

def readable_date(value):
 try:return dt.date.fromisoformat(value).strftime('%d.%m.%Y')
 except ValueError:return value

def make_pdf(c,rows,old,title):
 fonts=[Path('C:/Windows/Fonts/arial.ttf'),Path('C:/Windows/Fonts/calibri.ttf'),Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')]
 font=next((p for p in fonts if p.exists()),None)
 if not font:raise RuntimeError('Nenalezen font s českou diakritikou.')
 if 'APUnicode12' not in pdfmetrics.getRegisteredFontNames():pdfmetrics.registerFont(TTFont('APUnicode12',str(font)))
 base='APUnicode12'
 dark=colors.HexColor('#202938');muted=colors.HexColor('#536174');line=colors.HexColor('#DCE2E8')
 styles={
  'title':ParagraphStyle('APTitle12',fontName=base,fontSize=16,leading=21,textColor=dark,spaceAfter=6),
  'section':ParagraphStyle('APSection12',fontName=base,fontSize=11,leading=16,textColor=dark,spaceBefore=13,spaceAfter=7),
  'day':ParagraphStyle('APDay12',fontName=base,fontSize=10,leading=14,textColor=dark,spaceBefore=9,spaceAfter=4),
  'body':ParagraphStyle('APBody12',fontName=base,fontSize=9,leading=14,textColor=dark),
  'small':ParagraphStyle('APSmall12',fontName=base,fontSize=8,leading=12,textColor=muted),
  'head':ParagraphStyle('APHead12',fontName=base,fontSize=9,leading=13,textColor=dark),
 }
 def para(value,style='body'):return Paragraph(html.escape(str(value)),styles[style])
 story=[para('AP DENÍK – '+title,'title'),para(f'Počet záznamů: {len(rows)+len(old)}','small'),Spacer(1,10)]
 actions=summarize(c,rows)
 if actions:
  story.append(para('Souhrn vykonaných činností','section'))
  data=[[para('Činnost','head'),para('Počet','head')]]
  for name,n in actions.most_common():data.append([para(name),para(str(n))])
  table=Table(data,colWidths=[435,75],repeatRows=1,hAlign='LEFT')
  table.setStyle(TableStyle([
   ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#EEF1F5')),
   ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#FAFBFC')]),
   ('LINEBELOW',(0,0),(-1,-1),0.35,line),
   ('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),9),('RIGHTPADDING',(0,0),(-1,-1),9),
   ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),
  ]))
  story.append(table)
 story.append(para('Přehled jednotlivých záznamů','section'))
 last_day=None
 for sid,day,lesson,subject,shared,coverage,note in rows:
  if day!=last_day:
   story.append(para(readable_date(day),'day'));last_day=day
  heading=('Činnost mimo vyučování' if lesson==0 else f'{lesson}. hodina – {subject}')
  block=[para(heading,'head')]
  if coverage.startswith('Práce s celou třídou'):
   block.append(para('Práce s celou třídou'))
  else:
   block.append(para('Typ práce: '+coverage,'small'))
   if shared:
    for action in shared.split('; '):
     if action.strip():block.append(para('• '+action.strip()))
  size,members=group_info(c,sid)
  if members:block.append(para('Žáci: '+', '.join('žák '+x for x in members.split('; ') if x),'small'))
  elif size:block.append(para(f'Počet žáků: {size}','small'))
  for code,level,acts in details(c,sid):
   block.append(para('Žák '+code+': '+(acts or level),'small'))
  if note:block.append(para('Doplnění: '+note,'small'))
  block.extend([Spacer(1,5),HRFlowable(width='100%',thickness=0.5,color=line),Spacer(1,6)])
  story.append(KeepTogether(block))
 if old:
  story.append(para('Starší jednotlivé záznamy','section'))
  for day,lesson,subject,pupil,activity,coverage,note in old:
   story.append(para(f'{readable_date(day)} · {lesson}. hodina · {subject} · žák {pupil}: {activity}'))
 output=io.BytesIO()
 def footer(canvas,doc):
  canvas.saveState();canvas.setFont(base,8);canvas.setFillColor(muted)
  canvas.drawRightString(doc.pagesize[0]-40,25,f'Strana {doc.page}')
  canvas.restoreState()
 SimpleDocTemplate(output,pagesize=(595.28,841.89),leftMargin=42,rightMargin=42,topMargin=40,bottomMargin=43).build(story,onFirstPage=footer,onLaterPages=footer)
 return output.getvalue()

def report(c,start,end,label,filename):
 rows,old=fetch(c,start,end)
 st.metric('Počet záznamů',len(rows)+len(old))
 actions=summarize(c,rows)
 if actions:
  st.subheader('Souhrn vykonaných činností')
  st.dataframe([{'Činnost':name,'Počet':n} for name,n in actions.most_common()],hide_index=True,width='stretch')
 if rows:
  st.subheader('Přehled jednotlivých záznamů')
  previous=None
  for sid,day,lesson,subject,shared,coverage,note in rows:
   if day!=previous:
    st.markdown('**'+readable_date(day)+'**');previous=day
   with st.expander(('Mimo vyučování' if lesson==0 else f'{lesson}. hodina')+' · '+subject):
    if coverage.startswith('Práce s celou třídou'):
     st.write('Práce s celou třídou')
    else:
     st.write('Typ práce:',coverage)
     for action in shared.split('; '):
      if action.strip():st.write('• '+action.strip())
    size,members=group_info(c,sid)
    if members:st.write('Žáci:',members)
    elif size:st.write('Počet žáků:',size)
    if note:st.write('Doplnění:',note)
 if old:
  st.subheader('Starší jednotlivé záznamy')
  for day,lesson,subject,pupil,activity,coverage,note in old:
   st.write(readable_date(day),f'{lesson}. hodina',subject,'Žák '+pupil,activity)
 if rows or old:
  try:st.download_button('Stáhnout PDF sestavu',make_pdf(c,rows,old,label),file_name=filename,mime='application/pdf',key='pdf_'+filename)
  except Exception as e:st.error('PDF se nepodařilo vytvořit: '+str(e))
 else:st.info('V tomto období nejsou záznamy.')

st.set_page_config(page_title='AP DENÍK 1.4',layout='wide')
st.markdown("""<style>
.block-container {max-width: 980px; padding-top: 1.7rem;}
h1,h2,h3 {letter-spacing: -.025em;}
div[data-testid='stMetric'] {border: 1px solid #ddd; padding: 12px; border-radius: 10px;}
</style>""", unsafe_allow_html=True)
st.title('AP DENÍK · 1.4')
st.caption('Pracovní záznamy asistentky pedagoga · bez jmen žáků')
if 'ap_connection' not in st.session_state:
 st.session_state.ap_connection=connect()
c=st.session_state.ap_connection
st.info('Záznamy jsou dostupné pouze během aktuální relace. Na konci práce si stáhni denní PDF. Po zavření relace nebo restartu aplikace se mohou ztratit.')
page=st.radio('Část aplikace',['Pracovní den','Denní přehled'],horizontal=True)
if page=='Pracovní den':
 day=st.date_input('Datum',dt.date.today(),key='workday')
 st.subheader('Nový záznam')
 st.write('**Vyučovací hodina nebo jiná práce**')
 mode=st.radio('Kdy činnost probíhala?', ['Během vyučování','Mimo vyučování'],horizontal=True)
 if mode=='Během vyučování':
  n=st.selectbox('Vyučovací hodina',list(range(1,10)))
  sub=st.selectbox('Předmět',SUBJECTS)
  kind=st.radio('Jakou práci asistentka vykonávala?', ['Práce s celou třídou','Cílená podpora žáků se SVP','Ostatní práce'],horizontal=False)
 else:
  n=0
  sub='Činnost mimo vyučování'
  kind='Ostatní práce'
 st.divider()
 chosen=[]
 if kind=='Práce s celou třídou':
  st.write('**Práce s celou třídou**')
  st.caption('Není nutné vybírat jednotlivé činnosti ani žáky.')
  chosen=['Práce s celou třídou']
 else:
  st.markdown('#### Vykonané činnosti')
  if kind=='Cílená podpora žáků se SVP':
   support_scope=st.radio('Komu byla podpora poskytována?', ['Jednomu žákovi','Skupině žáků'],key='support_scope')
   st.caption('Vyber konkrétní činnosti podle skutečně poskytované podpory. Lze označit více položek.')
   categories=['Práce s učivem a zadáním','Pozornost, chování a sociální podpora']
  else:
   st.caption('Vyber organizační nebo jinou vykonanou práci.')
   categories=[x for x in CATALOG if x not in ('Práce s učivem a zadáním','Pozornost, chování a sociální podpora')]
  category=st.selectbox('Oblast činnosti',categories,key='work_category')
  st.write('**Konkrétní činnosti**')
  if 'work_activities' not in st.session_state:st.session_state.work_activities=[]
  def update_activity(act,key):
   if st.session_state.get(key):
    if act not in st.session_state.work_activities:st.session_state.work_activities.append(act)
   elif act in st.session_state.work_activities:st.session_state.work_activities.remove(act)
  for i,act in enumerate(CATALOG[category]):
   key='activity_'+str(i)+'_'+category
   st.checkbox(act,key=key,on_change=update_activity,args=(act,key))
  chosen=[a for a in st.session_state.work_activities if any(a in CATALOG[cat] for cat in categories)]
  if chosen:st.caption('Vybráno: '+' · '.join(chosen))
 custom=st.text_area('Vlastní doplnění (nepovinné)',height=80,placeholder='Jen pokud potřebuješ uvést něco dalšího')
 group_members=[]
 if kind=='Cílená podpora žáků se SVP':
  if support_scope=='Jednomu žákovi':
   individual=st.selectbox('Označení žáka (nepovinné)', ['Neuvedeno']+['Žák '+x for x in 'ABCDEF'])
   group_members=[] if individual=='Neuvedeno' else [individual.replace('Žák ','')]
  else:
   group_members=st.multiselect('Označení žáků (nepovinné)',list('ABCDEF'),format_func=lambda x:'Žák '+x)
 note=custom.strip()
 if st.button('Uložit záznam',type='primary'):
  if kind!='Práce s celou třídou' and not chosen and not note:
   st.error('Vyber alespoň jednu činnost nebo doplň vlastní zápis.')
  else:
   with c:
    cur=c.execute('INSERT INTO sessions(day,lesson,subject,shared,coverage,note) VALUES(?,?,?,?,?,?)',
       (day.isoformat(),n,sub,'; '.join(chosen),(kind+' – '+support_scope.lower()) if kind=='Cílená podpora žáků se SVP' else kind,note))
    if group_members:
     c.execute('INSERT INTO session_groups(session_id,group_size,members) VALUES(?,?,?)',
       (cur.lastrowid,None,'; '.join(group_members)))
   # Vyčistit jen ovládací prvky aktivit, které se v tomto záznamu použily.
   if 'work_activities' in st.session_state:st.session_state.work_activities=[]
   for cat in CATALOG:
    for i in range(len(CATALOG[cat])):
     st.session_state.pop('activity_'+str(i)+'_'+cat,None)
   st.success('Záznam byl uložen.')
 st.divider()
 st.subheader('Uložené záznamy za vybraný den')
 today=c.execute('SELECT id,lesson,subject,shared,coverage,note FROM sessions WHERE day=? ORDER BY lesson,id',(day.isoformat(),)).fetchall()
 if not today:st.info('Zatím žádný záznam.')
 for sid,lesson,subject,acts,coverage,memo in today:
  with st.expander(('Mimo vyučování' if lesson==0 else f'{lesson}. hodina')+' · '+subject):
   st.write('Typ práce:',coverage)
   if acts:st.write('Činnosti:',acts)
   size,members=group_info(c,sid)
   if members:st.write('Žáci:',members)
   if memo:st.write('Doplnění:',memo)
   if st.button('Smazat tento záznam',key=f'del_{sid}'):
    with c:
     c.execute('DELETE FROM session_groups WHERE session_id=?',(sid,))
     c.execute('DELETE FROM session_pupils WHERE session_id=?',(sid,))
     c.execute('DELETE FROM sessions WHERE id=?',(sid,))
    st.rerun()
elif page=='Denní přehled':
 d=st.date_input('Den',dt.date.today(),key='daily');report(c,d.isoformat(),d.isoformat(),'denní sestava '+d.isoformat(),'AP_DENIK_den_'+d.isoformat()+'.pdf')
