import streamlit as st
from streamlit_lottie import st_lottie
import streamlit_scrollable_textbox as stx

import pathlib
import requests
import json

import whisper
from whisper.utils import get_writer
from pytube import YouTube

from utils import *  # Assurez-vous que ce fichier est accessible et contient les fonctions nécessaires

def main():
    """
    Fonction principale
    """
    
    st.set_page_config(
        page_title="AI Audio Transcriber",
        page_icon="./assets/favicon.png",
        layout="centered",
        initial_sidebar_state="expanded",
        menu_items={
    
        })

    st.title("AI Audio Transcriber")
    hide_footer()  # type: ignore
    # Charger et afficher l'animation
    anim = lottie_local("C:\\Users\\User\\Downloads\\Hackathon Projet  Teranga AI\\AIAudioTranscriber-master\\assets\\animations\\transcriber.json")  # type: ignore
    st_lottie(anim,  # type: ignore
              speed=1,
              reverse=False,
              loop=True,
              quality="medium",  # low; medium; high
              height=400,
              width=400,
              key=None)

    # Initialiser les variables d'état de session
    if "page_index" not in st.session_state:
        st.session_state["page_index"] = 0
        st.session_state["model_path"] = ""
        st.session_state["input_mode"] = ""
        st.session_state["file_path"] = ""
        st.session_state["transcript"] = ""
        st.session_state["lang"] = ""
        st.session_state["segments"] = []

    model_list = {"Captain": r"./AIAudioTranscriber-master/assets/models/base.pt",
                  "Major": r"./AIAudioTranscriber-master/asset/models/small.pt",
                  "Colonel": r"./AIAudioTranscriber-master/assets/models/medium.pt",
                  "General": r"./AIAudioTranscriber-master/assets/models/large-v2.pt"}

    # Créer un composant de saisie
    input_mode = st.sidebar.selectbox(
        label="Input Mode",
        options=["Youtube Video URL", "Upload Audio File", "Online Audio URL"])
    st.session_state["input_mode"] = input_mode

    # Créer un formulaire sur la barre latérale pour accepter les données et paramètres
    with st.sidebar.form(key="input_form", clear_on_submit=False):

        # Composant imbriqué pour prendre l'entrée de l'utilisateur pour le fichier audio
        if input_mode == "Upload Audio File":
            uploaded_file = st.file_uploader(label="Upload your audio📁", type=["wav", "mp3", "m4a"], accept_multiple_files=False)
        elif input_mode == "Youtube Video URL":
            yt_url = st.text_input(label="Paste URL for Youtube Video 📋")
        else:
            aud_url = st.text_input(label="Enter URL for Audio File 🔗 ")

        # Composant imbriqué pour la sélection de la taille du modèle
        model_choice = st.radio(label="Choose Your Transcriber 🪖", options=list(model_list.keys()))
        st.session_state["model_path"] = model_list[model_choice]
        
        # Composant optionnel pour sélectionner le segment du clip à utiliser pour la transcription
        extra_configs = st.expander("Choose Segment ✂")
        with extra_configs:
            start = st.number_input("Start time for the media (sec)", min_value=0, step=1)
            duration = st.number_input("Duration (sec) - negative implies till the end", min_value=-1, max_value=30, step=1)
        
        submitted = st.form_submit_button(label="Generate Transcripts✨")
        if submitted:

            # Créer des sous-répertoires pour les entrées et sorties
            APP_DIR = pathlib.Path(__file__).parent.absolute()
            INPUT_DIR = APP_DIR / "input"
            INPUT_DIR.mkdir(exist_ok=True)

            # Charger l'audio à partir de la source d'entrée sélectionnée
            if input_mode == "Upload Audio File":
                if uploaded_file is not None:
                    grab_uploaded_file(uploaded_file, INPUT_DIR)
                    get_transcripts()
                else:
                    st.warning("Please🙏 upload a relevant audio file")
            elif input_mode == "Youtube Video URL":
                if yt_url and validate_YT_link(yt_url):  # type: ignore
                    grab_youtube_video(yt_url, INPUT_DIR)
                    get_transcripts()
                else:
                    st.warning("Please🙏 enter a valid URL for Youtube video")
            else:
                if aud_url and aud_url.startswith("https://"):
                    grab_youtube_video(aud_url, INPUT_DIR)
                    get_transcripts()
                else:
                    st.warning("Please🙏 enter a valid URL for desired video")

    # Si une transcription est disponible, afficher le texte
    if st.session_state["transcript"] != "" and st.session_state["lang"] != "":
        col1, col2 = st.columns([4, 4], gap="medium")
        
        # Afficher la transcription générée
        with col1:
            st.markdown("### Detected language🌐:")
            st.markdown(f"{st.session_state['lang']}")
            st.markdown("### Generated Transcripts📃: ")
            stx.scrollableTextbox(st.session_state["transcript"]["text"], height=300)
        
        # Afficher l'audio original
        with col2:
            if st.session_state["input_mode"] == "Youtube Video URL":
                st.markdown("### Youtube Video ▶️")
                st.video(yt_url)
            st.markdown("### Original Audio 🎵")
            with open(st.session_state["file_path"], "rb") as f:
                st.audio(f.read())
            
            # Bouton de téléchargement
            st.markdown("### Save Transcripts📥")
            out_format = st.radio(label="Choose Format", options=["Text File", "SRT File", "VTT File"])
            transcript_download(out_format)


def grab_uploaded_file(uploaded_file, INPUT_DIR: pathlib.Path):
    """
    Méthode pour stocker le fichier audio téléchargé sur le serveur
    """
    try:
        print("--------------------------------------------")
        print("Attempting to load uploaded audio file ...")
        # Extraire le format du fichier
        upload_name = uploaded_file.name
        upload_format = upload_name.split(".")[-1]
        # Créer le nom du fichier
        input_name = f"audio.{upload_format}"
        st.session_state["file_path"] = INPUT_DIR / input_name
        # Sauvegarder le fichier audio sur le serveur
        with open(st.session_state["file_path"], "wb") as f:
            f.write(uploaded_file.read())
        print("Successfully loaded uploaded audio")
    except:
        st.error("😿 Failed to load uploaded audio file")


def grab_youtube_video(url: str, INPUT_DIR: pathlib.Path):
    """
    Méthode pour récupérer le codec audio d'une vidéo YouTube et l'enregistrer sur le serveur
    """
    try:
        print("--------------------------------------------")
        print("Attempting to fetch audio from Youtube ...")
        video = YouTube(url).streams.get_by_itag(140).download(INPUT_DIR, filename="audio.mp3")
        print("Successfully fetched audio from Youtube")
        st.session_state["file_path"] = INPUT_DIR / "audio.mp3"
    except:
        st.error("😿 Failed to fetch audio from YouTube")


def grab_online_video(url: str, INPUT_DIR: pathlib.Path):
    """
    Méthode pour récupérer un fichier audio en ligne et l'enregistrer sur le serveur
    """
    try:
        print("--------------------------------------------")
        print("Attempting to fetch remote audio file ...")
        # Télécharger le fichier
        r = requests.get(url, allow_redirects=True)
        # Extraire le format du fichier
        file_name = url.split("/")[-1]
        file_format = url.split(".")[-1]
        # Créer le nom du fichier
        input_name = f"audio.{file_format}"
        st.session_state["file_path"] = INPUT_DIR / input_name
        # Sauvegarder sur le serveur
        with open(st.session_state["file_path"], "wb") as f:
            f.write(r.content)
        print("Successfully fetched remote audio")
    except:
        st.error("😿 Failed to fetch audio file")


@st.cache_resource
def get_model(model_type: str = 'tiny'):
    """
    Méthode pour charger le modèle Whisper sur le disque
    """
    try:
        print("--------------------------------------------")
        print("Attempting to load Whisper ...")
        model = whisper.load_model(model_type)
        print("Successfully loaded Whisper")
        return model
    except:
        print("Failed to load model")
        st.error("😿 Failed to load model")


def get_transcripts():
    """
    Méthode pour générer des transcriptions pour le fichier audio souhaité
    """
    try:
        # Charger Whisper
        model = get_model()
        # Charger l'audio et le découper/trimmer pour l'adapter à 30 secondes
        audio = whisper.load_audio(st.session_state["file_path"])
        # audio = whisper.pad_or_trim(audio)
        # Pass the audio file to the model and generate transcripts
        print("--------------------------------------------")
        print("Attempting to generate transcripts ...")
        result = model.transcribe(audio)
        print(result)
        print("Succesfully generated transcripts")
        # Grab the text and update it in session state for the app
        st.session_state["transcript"] = result["text"]
        st.session_state["lang"] = match_language(result["language"])
        st.session_state["segments"] = result["segments"]
        st.session_state["transcript"] = result
        # Save Transcipts:
        st.balloons()
    except:
        st.error("😿 Model Failed to genereate transcripts")

def match_language(lang_code:str)->str:
    """
    Method to match the language code detected by Whisper to full name of the language
    """
    with open("./language.json","rb") as f:
        lang_data = json.load(f)
    
    return lang_data[lang_code].capitalize()

def transcript_download(out_format:str):
    """
    Method to save transcipts in VTT format
    """

    # Create Output sub-directory if it does not exist already
    APP_DIR = pathlib.Path(__file__).parent.absolute()
    OUTPUT_DIR = APP_DIR / "output"
    OUTPUT_DIR.mkdir(exist_ok=True)

    #Create a dict of out_format and the file type
    file_type_dict = {"Text File":"txt","SRT File":"srt","VTT File":"vtt"}

    #Select the file type
    file_type = file_type_dict[out_format]

    if out_format in file_type_dict.keys():
        # Generate Transcript file as per choice
        get_writer(file_type, OUTPUT_DIR)(st.session_state["transcript"], st.session_state["file_path"])
        # Generate SRT File for Transcript  
        with open(OUTPUT_DIR/f'audio.{file_type}', "r", encoding ="utf-8") as f:
            st.download_button(
                            label="Click to download 🔽",
                            data = f,
                            file_name=f"transcripts.{file_type}",
                            )



if __name__ == "__main__":
    main()
     