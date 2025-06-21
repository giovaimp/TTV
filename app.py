import streamlit as st
from moviepy.editor import *
from gtts import gTTS
import tempfile
import os
import stripe

# ------------------ STRIPE EINSTELLUNGEN ------------------
stripe.api_key = "sk_test_YOUR_SECRET_KEY"  # Ersetze mit deinem Stripe Secret Key
STRIPE_PRODUCT_ID = "prod_YOUR_PRODUCT_ID"  # Ersetze mit deiner Produkt-ID

# ------------------ SPRACHEN, FONTS, POSITIONEN ------------------
LANGUAGES = {"Deutsch": "de", "Englisch": "en", "Französisch": "fr", "Spanisch": "es"}
FONTS = ["Arial", "Courier-New", "Helvetica", "Times-New-Roman"]
POSITIONS = {"Oben": ("center", "top"), "Mitte": "center", "Unten": ("center", "bottom")}

# ------------------ FUNKTIONEN ------------------

def apply_transition(clip1, clip2, duration=1):
    return concatenate_videoclips([clip1.crossfadeout(duration), clip2.crossfadein(duration)], method="compose")

def create_text_scene(text, audio_path, duration, bg_path=None, fontsize=50, color="white", font="Arial", position="center"):
    if bg_path:
        if bg_path.endswith(".mp4"):
            bg = VideoFileClip(bg_path).resize((1280, 720)).set_duration(duration)
        else:
            bg = ImageClip(bg_path).resize((1280, 720)).set_duration(duration)
    else:
        bg = ColorClip((1280, 720), color=(0, 0, 0)).set_duration(duration)

    txt = TextClip(text, fontsize=fontsize, color=color, font=font, method="caption", size=(1200, None), align="center")
    txt = txt.set_position(position).set_duration(duration).fadein(0.5).fadeout(0.5)
    txt = txt.fx(vfx.zoom_in, final_scale=1.05, duration=duration)

    scene = CompositeVideoClip([bg, txt])
    audio = AudioFileClip(audio_path)
    scene = scene.set_audio(audio)
    return scene

def generate_audio(text, lang, idx):
    audio_path = f"temp_audio_{idx}.mp3"
    tts = gTTS(text=text, lang=lang)
    tts.save(audio_path)
    return audio_path

def build_video(texts, lang, bg_path, fontsize, color, font, position):
    clips = []
    audio_files = []
    for i, text in enumerate(texts):
        audio_path = generate_audio(text, lang, i)
        audio_files.append(audio_path)
        audio_clip = AudioFileClip(audio_path)
        duration = audio_clip.duration
        clip = create_text_scene(text, audio_path, duration, bg_path, fontsize, color, font, position)
        clips.append(clip)
    final = clips[0]
    for clip in clips[1:]:
        final = apply_transition(final, clip)
    output_path = "output.mp4"
    final.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac", verbose=False, logger=None)
    for f in audio_files:
        os.remove(f)
    return output_path

# ------------------ STREAMLIT UI ------------------

st.title("🎬 Text-to-Video App mit Abo-System")

# Session-Status
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "subscribed" not in st.session_state:
    st.session_state.subscribed = False

def dummy_login():
    st.session_state.logged_in = True
    st.success("Du bist eingeloggt!")

def dummy_logout():
    st.session_state.logged_in = False
    st.session_state.subscribed = False
    st.success("Du bist ausgeloggt!")

if not st.session_state.logged_in:
    if st.button("Login (Demo)"):
        dummy_login()
    st.stop()

st.sidebar.button("Logout", on_click=dummy_logout)

if not st.session_state.subscribed:
    st.warning("Kein aktives Abo – bitte abonnieren, um Videos zu erstellen.")

    prices = stripe.Price.list(product=STRIPE_PRODUCT_ID)
    for price in prices.data:
        if st.button(f"Abo kaufen: {price.nickname} – {price.unit_amount / 100:.2f} {price.currency.upper()}"):
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{'price': price.id, 'quantity': 1}],
                mode='subscription',
                success_url='https://deineapp.com/success',
                cancel_url='https://deineapp.com/cancel',
            )
            st.write(f"[Zahlung starten]({checkout_session.url})")
    st.stop()

# ------------------ VIDEO FORMULAR ------------------

st.subheader("🎙️ Deine Video-Szenen")

text_input = st.text_area("Texte für Szenen (durch Leerzeile trennen):", height=200)
bg_file = st.file_uploader("Hintergrund (Bild oder Video)", type=["png", "jpg", "jpeg", "mp4"])
fontsize = st.slider("Schriftgröße", 20, 100, 50)
color = st.color_picker("Schriftfarbe", "#FFFFFF")
font = st.selectbox("Schriftart", FONTS)
position = st.selectbox("Textposition", list(POSITIONS.keys()))
lang = st.selectbox("Sprache (für Stimme)", list(LANGUAGES.keys()))

if st.button("📽️ Video erstellen"):
    if not text_input.strip():
        st.warning("Bitte Text eingeben!")
    else:
        texts = [t.strip() for t in text_input.split("\n\n") if t.strip()]
        bg_path = None
        if bg_file:
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(bg_file.name)[1]) as f:
                f.write(bg_file.read())
                bg_path = f.name
        with st.spinner("Video wird erstellt..."):
            output_path = build_video(texts, LANGUAGES[lang], bg_path, fontsize, color, font, POSITIONS[position])
        st.success("✅ Video fertig!")
        st.video(output_path)
        with open(output_path, "rb") as f:
            st.download_button("📥 Download", data=f, file_name="video.mp4")
        os.remove(output_path)
        if bg_path and os.path.exists(bg_path):
            os.remove(bg_path)
