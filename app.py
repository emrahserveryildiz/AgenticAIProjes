from __future__ import annotations

import re
import uuid
from pathlib import Path

import streamlit as st

from agentic_it import database
from agentic_it.config import API_KEY, DEMO_MODE, KNOWLEDGE_DIR, MODEL
from agentic_it.evaluation import run_retrieval_evaluation
from agentic_it.knowledge import KnowledgeBase
from agentic_it.orchestrator import SupportOrchestrator

st.set_page_config(page_title="Nöbetçi · IT Support Agent", page_icon="🧭", layout="wide")

st.markdown("""
<style>
html, body, [class*="css"] { font-family: 'Segoe UI', Arial, sans-serif; }
h1, h2, h3 { font-family: 'Segoe UI', Arial, sans-serif; letter-spacing: -.03em; }
.block-container { max-width: 1240px; padding-top: 2rem; padding-bottom: 3rem; }
.eyebrow { color:#527199; font-size:.76rem; font-weight:700; letter-spacing:.12em; text-transform:uppercase; }
.hero { background:linear-gradient(120deg,#102340 0%,#173c67 58%,#276ef1 100%); padding:30px 34px; border-radius:20px; color:white; margin:0 0 24px 0; }
.hero h1 { color:white; margin:.25rem 0 .55rem; font-size:2rem; }
.hero p { color:#dce9f8; margin:0; max-width:760px; }
.agent-card { background:white; border:1px solid #e6ebf2; border-radius:14px; padding:15px 17px; min-height:95px; }
.agent-name { color:#54708e; font-size:.75rem; text-transform:uppercase; letter-spacing:.08em; font-weight:700; }
.agent-detail { color:#172a43; font-weight:600; margin-top:7px; font-size:.92rem; }
.subtle { color:#718198; font-size:.9rem; }
.source-card { border-left:3px solid #276ef1; padding:9px 13px; background:#f6f9fd; border-radius:0 10px 10px 0; margin:8px 0; }
.ticket-card { background:#fff8e9; border:1px solid #f5d89a; padding:16px; border-radius:13px; }
div[data-testid="stMetric"] { background:white; border:1px solid #e6ebf2; padding:14px 17px; border-radius:14px; }
button[kind="primary"] { border-radius:10px; font-weight:700; }
</style>
""", unsafe_allow_html=True)

database.init_db()
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "chat" not in st.session_state:
    st.session_state.chat = []
if "last_result" not in st.session_state:
    st.session_state.last_result = None
if "approved_ticket" not in st.session_state:
    st.session_state.approved_ticket = False
if "kb" not in st.session_state:
    st.session_state.kb = KnowledgeBase()

kb: KnowledgeBase = st.session_state.kb
agent = SupportOrchestrator(kb)

with st.sidebar:
    st.markdown("### 🧭 Nöbetçi")
    st.caption("Agentic IT Support Desk")
    if DEMO_MODE:
        st.info("Demo modu · API anahtarı yok. Akış yerel ve deterministik çalışıyor.")
    else:
        st.success(f"Model bağlantısı hazır · {MODEL}")
    st.divider()
    st.markdown("**Oturum hafızası**")
    memory = database.get_memory(st.session_state.session_id)
    if memory:
        for fact in memory:
            st.caption("• " + fact)
    else:
        st.caption("Henüz hatırlanacak bilgi yok.")
    if st.button("Bu oturumun hafızasını temizle", width="stretch"):
        database.clear_session(st.session_state.session_id)
        st.session_state.chat = []
        st.session_state.last_result = None
        st.rerun()
    st.divider()
    st.caption("Salt okunur demo araçları · Ticket için onay gerekir")
    st.caption("Oturum: " + st.session_state.session_id[:8])

st.markdown('<div class="hero"><div class="eyebrow" style="color:#b9d5ff">Agentic AI · IT Operations</div><h1>Tek bir talep. Bir ekip gibi çalışan ajanlar.</h1><p>Nöbetçi talebi sınıflandırır, runbook’larda kanıt arar, güvenli teşhis araçlarını çalıştırır ve çözüm ya da onay bekleyen bir destek kaydı hazırlar.</p></div>', unsafe_allow_html=True)

tab_support, tab_tickets, tab_eval, tab_kb, tab_arch = st.tabs(["Destek masası", "Ticket kuyruğu", "Değerlendirme", "Bilgi tabanı", "Mimari"])

with tab_support:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Uzman agent", "5", "Triage · Plan · RAG · Tools · Safety")
    c2.metric("Runbook kaynağı", str(len(kb.all_sources())), "Yerel Markdown")
    c3.metric("Demo araçları", "3", "Salt okunur")
    c4.metric("Yazma işlemi", "Onaylı", "Ticket öncesi")
    st.markdown("### Bir destek talebini incele")
    examples = {
        "VPN · Parola değişikliği": "Parolamı değiştirdikten sonra VPN bağlanmıyor. Ne yapmalıyım?",
        "E-posta · Gecikme": "Outlook açılıyor ama e-postalarım gecikmeli geliyor.",
        "Güvenlik · Şüpheli e-posta": "Ekinde dosya olan şüpheli bir e-posta geldi. Açmalı mıyım?",
        "Cihaz · Yavaşlık": "Laptopum bu sabah çok yavaşladı.",
    }
    selected = st.selectbox("Demo senaryosu", ["Kendim yazacağım", *examples.keys()], label_visibility="collapsed")
    initial = examples.get(selected, "")
    with st.form("incident_form", clear_on_submit=False):
        query = st.text_area("Sorunu kısaca anlatın", value=initial, height=105,
                             placeholder="Örn. Parola değişikliğinden sonra VPN bağlanmıyor; LAP-1042 cihazını kullanıyorum.")
        submitted = st.form_submit_button("Talebi incele", type="primary", width="stretch")
    if submitted:
        if not query.strip():
            st.warning("İncelemek için bir talep yazın.")
        else:
            with st.spinner("Triage, planlama, runbook arama ve güvenlik kontrolleri çalışıyor…"):
                result = agent.handle(st.session_state.session_id, query.strip())
            st.session_state.last_result = result
            st.session_state.approved_ticket = False
            st.session_state.chat.insert(0, {"query": query.strip(), "result": result})

    result = st.session_state.last_result
    if result:
        st.divider()
        left, right = st.columns([1.55, 1])
        with left:
            st.markdown("### Önerilen yanıt")
            st.markdown(result["answer"])
            if result.get("follow_up_question"):
                st.info("Takip sorusu: " + result["follow_up_question"])
            if result.get("warnings"):
                for warning in result["warnings"]:
                    st.warning(warning)
            with st.expander("Agent adımları ve iz", expanded=True):
                for step in result["steps"]:
                    st.markdown(f"**{step['agent']}** · {step['status']}  \n{step['detail']}")
                st.markdown("**Planın durma koşulları**")
                for stop in result["plan"].get("stop_conditions", []):
                    st.markdown(f"- {stop}")
        with right:
            st.markdown("### Olay özeti")
            st.markdown(f"**Kategori:** {result['triage'].get('category')}  \n**Öncelik:** {result['triage'].get('priority')}  \n**Güven:** {result['triage'].get('confidence', '—')}")
            if result["evidence"]:
                st.markdown("**Bulunan kanıtlar**")
                for item in result["evidence"]:
                    st.markdown(f"<div class='source-card'><b>{item['source']}</b> · {item['section']}<br><span class='subtle'>{item['text'][:230]}…</span></div>", unsafe_allow_html=True)
            if result["diagnostics"]:
                st.markdown("**Araç sonuçları**")
                for call in result["diagnostics"]:
                    with st.expander(call["tool"]):
                        st.json(call.get("result", {}))
            if result.get("ticket_recommended") and not st.session_state.approved_ticket:
                st.markdown("<div class='ticket-card'><b>Destek kaydı taslağı hazır</b><br>Ticket yalnızca aşağıdaki onaydan sonra oluşturulur.</div>", unsafe_allow_html=True)
                with st.expander("Ticket içeriğini gözden geçir"):
                    st.write("**" + result["ticket_title"] + "**")
                    st.write(result["ticket_description"])
                if st.button("Onayla ve ticket oluştur", type="primary", key="approve_ticket"):
                    ticket_id = database.create_ticket(st.session_state.session_id,
                        result["ticket_title"], result["ticket_description"],
                        result["triage"].get("category", "Other"), result["triage"].get("priority", "P3"))
                    database.log_event(st.session_state.session_id, "ticket_created", f"Ticket {ticket_id} kullanıcı onayıyla açıldı")
                    st.session_state.approved_ticket = True
                    st.session_state.last_ticket_id = ticket_id
                    st.rerun()
            elif st.session_state.approved_ticket:
                st.success(f"Ticket {st.session_state.get('last_ticket_id', '')} onayınızla oluşturuldu.")
        if result.get("safety_findings"):
            st.error("Güvenlik kontrolü nedeniyle önerilen yanıt ve aksiyon durduruldu.")

    if st.session_state.chat:
        with st.expander("Bu oturumdaki önceki incelemeler"):
            for item in st.session_state.chat[1:]:
                st.markdown("**Talep:** " + item["query"])
                st.caption(item["result"]["answer"][:360])
                st.divider()

with tab_tickets:
    tickets = database.list_tickets()
    st.markdown("### Oluşturulan destek kayıtları")
    st.caption("Bu proje yerel demo kuyruğu kullanır; gerçek ITSM sistemine bağlanmaz.")
    if tickets:
        st.dataframe(tickets, width="stretch", hide_index=True)
    else:
        st.info("Henüz ticket yok. Destek masasında bir taslağı inceleyip onaylayabilirsiniz.")
    st.markdown("### Denetim izi")
    events = database.list_events()
    if events:
        st.dataframe([{ "zaman (UTC)": e["created_at"], "oturum": e["session_id"][:8],
                        "olay": e["event_type"], "özet": e["summary"], "ayrıntı": e["details"]}
                      for e in events], width="stretch", hide_index=True)
    else:
        st.caption("Ajan çalıştırıldığında iz kayıtları burada görünür.")

with tab_eval:
    st.markdown("### RAG değerlendirme seti")
    st.caption("Küçük yerel benchmark: beklenen runbook kaynağının ilk 3 sonuçta görünmesi ve önemli terimlerin kapsanması.")
    if st.button("Değerlendirmeyi çalıştır", type="primary"):
        st.session_state.eval_result = run_retrieval_evaluation(kb)
    evaluation = st.session_state.get("eval_result")
    if evaluation:
        a, b = st.columns(2)
        a.metric("Kaynak isabet oranı", f"{evaluation['source_hit_rate']:.0%}")
        b.metric("Terim kapsamı", f"{evaluation['term_coverage']:.0%}")
        st.dataframe(evaluation["results"], width="stretch", hide_index=True)
    st.markdown("#### Yanıt kalite kontrol listesi")
    st.markdown("- Kaynak dayanağı ve alıntı biçimi  \n- Gizli bilgi istememe  \n- Güvenli adımlar ve eskalasyon  \n- İşlem öncesi insan onayı  \n- Belirsiz durumda açıklayıcı soru")

with tab_kb:
    st.markdown("### Runbook bilgi tabanı")
    st.caption("Markdown dosyaları RAG için küçük bölümlere ayrılır. Yüklenen dosyalar bu demo klasöründe saklanır.")
    for source in kb.all_sources():
        with st.expander(source["name"]):
            st.markdown(source["content"])
    uploaded = st.file_uploader("Markdown runbook ekle", type=["md", "txt"], help="En fazla 1 MB. Yüklemeden önce gizli bilgileri çıkarın.")
    if uploaded is not None:
        if uploaded.size > 1_000_000:
            st.error("Dosya 1 MB sınırını aşıyor.")
        else:
            safe_name = re.sub(r"[^a-zA-Z0-9_-]+", "_", Path(uploaded.name).stem).strip("_")[:70] or "runbook"
            if st.button("Dosyayı bilgi tabanına ekle", type="primary"):
                target = KNOWLEDGE_DIR / f"{safe_name}.md"
                KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
                target.write_text(uploaded.getvalue().decode("utf-8", errors="replace"), encoding="utf-8")
                kb.reload()
                database.log_event(st.session_state.session_id, "knowledge_added", f"{target.name} bilgi tabanına eklendi")
                st.success("Runbook eklendi. Yeni aramalarda kullanılabilir.")
                st.rerun()

with tab_arch:
    st.markdown("### Agent akışı")
    st.code("""Kullanıcı talebi
   ↓
Triage Agent ── kategori · öncelik · eksik bilgiler
   ↓
Planner Agent ── adımlar · durma koşulları
   ↓
RAG Retriever ── runbook parçaları · kaynak kanıtları
   ↓
Diagnostics Agent ── salt okunur tool calling
   ↓
Response Agent ── Türkçe yanıt · ticket taslağı · düşük hassasiyetli hafıza
   ↓
Safety Guardrails ── sır isteme / riskli öneri kontrolü
   ↓
İnsan onayı ── yerel ticket kuyruğuna yazma
   ↓
SQLite ── oturum hafızası · konuşmalar · ticket'lar · audit log""", language="text")
    st.markdown("### Teknikler ve sınırlar")
    st.markdown("- **RAG:** runbook parçalarını BM25 benzeri yerel retrieval ile bulur; cevapta kaynak gösterir.\n- **Multi-agent orchestration:** triage, planner, diagnostics ve response rolleri ayrı aşamalardır; her adım izlenebilir.\n- **Tool calling:** servis sağlığı ve cihaz envanteri için allowlist'teki salt okunur araçlar.\n- **Memory:** SQLite oturum hafızası ve yakın konuşma bağlamı; kullanıcı temizleyebilir.\n- **Human-in-the-loop:** ticket oluşturma için açık onay gerekir.\n- **Guardrails:** parola/MFA kodu isteme ve güvenlik korumasını kapatma önerilerini durdurur.\n- **Evaluation:** kaynak isabeti ve terim kapsamı metriği olan mini retrieval benchmark.\n- **Fallback:** API anahtarı yoksa deterministik demo davranışı. Ticket ve servis verileri yereldir; gerçek sistem entegrasyonu değildir.")

st.markdown("<div class='subtle' style='text-align:center;padding:22px 0 0'>Nöbetçi · Bootcamp final projesi için demo · Hassas veya gerçek kurumsal veriler yüklemeyin</div>", unsafe_allow_html=True)
