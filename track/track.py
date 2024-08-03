#  streamlit run iscritti.py --server.headless true

import streamlit as st
import pandas as pd
import numpy as np
import base64
import os 
from datetime import datetime
from streamlit_tags import st_tags_sidebar

# -------------------------- § 2 200 metri cronometrati 6 
# § 3 Velocità 6 
# § 4 Inseguimento individuale 9 
# § 5 Inseguimento a squadre 10 
# -------------------------- § 6 Chilometro e 500 metri contro il tempo 12 
# -------------------------- § 7 Corsa a punti 13 
# § 8 Keirin 15 
# § 9 Velocità a squadre 19 
# § 10 Madison 23 
# -------------------------- § 11 Scratch 25 
# § 12 Tandem 26 
# -------------------------- § 13 Corsa ad eliminazione 26 
# § 14 Gare di 6 giorni 27 
# § 15 Omnium 29 
# § 16 Giro Lanciato 31 
# -------------------------- § 17 Tempo Race 31 


st.set_page_config(layout="wide")

DATASET = "../data/Iscritti_173511.xls"
DATASET_WORK = DATASET + ".xls"
TRACK_LEN = 0.33333

# Events
M200  = "200 m"
Spr   = "Velocità"
IndP  = "Inseguimento individuale"
TeamP = "Inseguimento a squadre"
Km    = "km"
M500  = "500 m"
PtR   = "Corsa a punti"
Kei   = "Keirin"
TeamS = "Velocità a squadre"
Mad   = "Madison"
Scr   = "Scratch"
ElR   = "Eliminazione"
Omn   = "Omnium"
TempR = "Tempo Race"

name_all = "Tutte"
name_dist_short = "Dist. (km)"
name_cat_short   = "Cat."
name_pos_short   = "Pos."
name_tot_short   = "Tot."
name_batt_short  = "Batt."
name_laps_short  = "Giri"
name_event       = "Disciplina"
name_cat         = "Categoria"
name_dns         = "**DNS**"
name_dnf         = "**DNF**"
name_dsq         = "**DSQ**"
name_laps_gained = "**:green[Dors. giri guadagnati (`,`):]**"
name_laps_lost   = "**:red[Dors. giri persi (`,`):]**"
name_last_sprint = "Ultimo sprint"
name_time        = "Tempo"
name_title       = "Titolo"
name_title_com   = "Titolo e decisione"
name_class       = "Classifica"
name_decision    = "Decisione"
name_finals      = "Finali"
name_qualif      = "Qualificazioni"
name_results     = "Risultati"
name_startlist   = "Ordine partenti"


msg_multiple_nums = "Dorsale inserito più di una volta"
msg_missing_nums  = "Dorsale non presente nella lista partenti"


name_group_race_sprint_input = ("**:blue[Inserisci dorsali (`,`) per ogni sprint (`-`):]**",
                                "Inserisci tutti i dorsali dell'ultimo sprint per una corretta classifica.")
                                
name_group_race_el_input = "**:blue[Inserisci dorsali (`,`) in ordine inverso:]**"
name_pursuit_input = "**:blue[Inserisci dorsali (`,`) team (`-`) e batterie (`/`):]**"
name_time_input = "**Inserisci tempi** (`mm:ss.000`)"

def check_n_sprint(n_in, n_max):
    if n_in > n_max:
        st.error(f"Il numero di sprint inseriti ({n_in}) è maggiore degli sprint previsti ({n_max})!")
        st.stop()
            
def check_n_rider(startlist, rider_num, sprint_num=None, is_in=False):
    status = True
    if not is_in:
        if (rider_num not in startlist):
            if sprint_num:
                st.error(f"Dorsale {rider_num} (sprint n. {sprint_num+1}) non presente tra i partenti. Rimuovilo.")
            else:
                st.error(f"Dorsale {rider_num} non presente tra i partenti. Rimuovilo.")
            status = False
    else:
        if (rider_num in startlist):
            st.error(f"Dorsale {rider_num} già inserito. Rimuovilo.")
            status=False

    return status
        

def check_sprint_len(sprint, sprint_num, startlist):
    if np.isin(sprint,startlist).sum() < 4:
        st.error(f"Sprint n. {sprint_num+1} deve avere almeno 4 atleti partenti.")
        return False
    return True

def get_title_decision(kind, event, cat, n_laps, n_sprint=None, title="", decision=""):

    if title=="":
        if n_sprint is not None:
            title = f"{kind} - {event} {cat} - {n_laps} giri ({n_sprint} sprint)"
        else:
            title = f"{kind} - {event} {cat} - {n_laps} giri"

        if event in [ElR, M200, M500, Km]:
            title = f"{kind} - {event} {cat}"

    title    = st.sidebar.text_input(name_title_com, title, placeholder=name_title)
    decision = st.sidebar.text_area(name_decision, decision, label_visibility ="collapsed", placeholder=name_decision)

    return title, decision

def get_dns_dnf_dsq():

    col_dns, col_dnf, col_dsq = st.sidebar.columns(3)
    with col_dns:
        dns_list = get_sprint_from_text(st.text_input(name_dns, ""))
        dns_list = np.array(dns_list).flatten()
    with col_dnf:
        dnf_list = get_sprint_from_text(st.text_input(name_dnf, ""))
        dnf_list = np.array(dnf_list).flatten()
    with col_dsq:
        dsq_list = get_sprint_from_text(st.text_input(name_dsq, ""))
        dsq_list = np.array(dsq_list).flatten()

    return dns_list, dnf_list, dsq_list
    

### Events properties
EVENTS_DICT = {M200:   {"do": 0,  "shortname":"200 m",      "D":{}, "DLS":{},  "kind":"timeSprint"    }, 
               Spr:    {"do": 0,  "shortname":"Vel.",       "D":{}, "DLS":{},  "kind":""    }, 
               IndP:   {"do": 1,  "shortname":"Ins. Ind.",  "D":{}, "DLS":{},  "kind":"time"    },
               TeamP:  {"do": 1,  "shortname":"Ins. Sq.",   "D":{}, "DLS":{},  "kind":"time"    }, 
               Km:     {"do": 1,  "shortname":"km",         "D":{}, "DLS":{},  "kind":"timeSprint"    },   
               M500:   {"do": 1,  "shortname":"500 m",      "D":{}, "DLS":{},  "kind":"timeSprint"    },
               PtR:    {"do": 1,  "shortname":"CP",         "D":{}, "DLS":{},  "kind":"group"    },
               Kei:    {"do": 0,  "shortname":"Keirin",     "D":{}, "DLS":{},  "kind":""    },
               TeamS:  {"do": 1,  "shortname":"Vel. Sq.",   "D":{}, "DLS":{},  "kind":"time"    },
               Mad:    {"do": 1,  "shortname":"Madison",    "D":{}, "DLS":{},  "kind":""    },
               Scr:    {"do": 1,  "shortname":"Scratch",    "D":{}, "DLS":{},  "kind":"group"    },
               ElR:    {"do": 1,  "shortname":"El",         "D":{}, "DLS":{},  "kind":"groupEl"    },
               Omn:    {"do": 1,  "shortname":"Omn",        "D":{}, "DLS":{},  "kind":""    },
               TempR:  {"do": 1,  "shortname":"TR",         "D":{}, "DLS":{},  "kind":"group"    }}

### Active events
EVENTS = [k for k in EVENTS_DICT.keys() if EVENTS_DICT[k]["do"]==1]

### Distance
EVENTS_DICT[M200]["D"]    = {"EL":0.8, "DE":0.8, "JU":0.8, "DJ":0.8, "AL":0.8, "DA":0.8, "ES":0.8, "ED":0.8}
EVENTS_DICT[Spr]["D"]     = {}
EVENTS_DICT[IndP]["D"]    = {"EL":4, "DE":3, "JU":3, "DJ":2, "AL":3, "DA":2}
EVENTS_DICT[TeamP]["D"]   = {"EL":4, "DE":4, "JU":4, "DJ":4, "AL":3, "DA":3}
EVENTS_DICT[Km]["D"]      = {"EL":1, "DE":1, "JU":1, "DJ":1, "AL":1, "DA":1, "ES":1, "ED":1}
EVENTS_DICT[M500]["D"]    = {"EL":0.5, "DE":0.5, "JU":0.5, "DJ":0.5, "AL":0.5, "DA":0.5, "ES":0.5, "ED":0.5}
EVENTS_DICT[PtR]["D"]     = {"EL":30, "DE":20, "JU":20, "DJ":16, "AL":16, "DA":12, "ES":12, "ED":12}
EVENTS_DICT[Kei]["D"]     = {"EL":0.5, "DE":0.5, "JU":0.5, "DJ":0.5, "AL":0.5, "DA":0.5, "ES":0.5, "ED":0.5}
EVENTS_DICT[TeamS]["D"]   = {}
EVENTS_DICT[Mad]["D"]     = {}
EVENTS_DICT[Scr]["D"]     = {"EL":15, "DE":10, "JU":10, "DJ":7.5, "AL":7.5, "DA":5, "ES":5, "ED":5}
EVENTS_DICT[ElR]["D"]     = {"EL":0, "DE":0, "JU":0, "DJ":0, "AL":0, "DA":0, "ES":0, "ED":0}
EVENTS_DICT[Omn]["D"]     = {}
EVENTS_DICT[TempR]["D"]   = {"EL":10, "DE":7.5, "JU":7.5, "DJ":5, "AL":5, "DA":4, "ES":4, "ED":4}

### Distance, Laps, Sprints
EVENTS_DICT[M200]["DLS"]  = {k:[v,np.ceil(v/TRACK_LEN * 2) / 2, 0] for k,v in EVENTS_DICT[M200]["D"].items()}
EVENTS_DICT[Spr]["DLS"]   = {}
EVENTS_DICT[IndP]["DLS"]  = {k:[v,np.ceil(v/TRACK_LEN * 2) / 2, 0] for k,v in EVENTS_DICT[IndP]["D"].items()}
EVENTS_DICT[TeamP]["DLS"] = {k:[v,np.ceil(v/TRACK_LEN * 2) / 2, 0] for k,v in EVENTS_DICT[TeamP]["D"].items()}
EVENTS_DICT[Km]["DLS"]    = {k:[v,np.ceil(v/TRACK_LEN * 2) / 2, 0] for k,v in EVENTS_DICT[Km]["D"].items()}
EVENTS_DICT[M500]["DLS"]  = {k:[v,np.ceil(v/TRACK_LEN * 2) / 2, 0] for k,v in EVENTS_DICT[M500]["D"].items()}
EVENTS_DICT[PtR]["DLS"]   = {k:[v,np.round(v/TRACK_LEN, 0), np.round(v/TRACK_LEN, 0)//6] for k,v in EVENTS_DICT[PtR]["D"].items()}
EVENTS_DICT[Kei]["DLS"]   = {}
EVENTS_DICT[TeamS]["DLS"] = {}
EVENTS_DICT[Mad]["DLS"]   = {}
EVENTS_DICT[Scr]["DLS"]   = {k:[v,np.round(v/TRACK_LEN, 0), 1] for k,v in EVENTS_DICT[Scr]["D"].items()}
EVENTS_DICT[ElR]["DLS"]   = {k:[0,0,0] for k,v in EVENTS_DICT[ElR]["D"].items()} 
EVENTS_DICT[Omn]["DLS"]   = {}
EVENTS_DICT[TempR]["DLS"] = {k:[v,np.round(v/TRACK_LEN, 0), np.round(v/TRACK_LEN, 0)-4] for k,v in EVENTS_DICT[TempR]["D"].items()}

sort_categories = ["G1", "G2", "G3", "G4", "G5", "G6", "ES", "ED", "AL", "DA", "JU", "DJ", "DE", "EL"]

default_cols_to_hide = ["IdGara", "NomeGara", "CodiceFCI", "Cod. Soc.", "Naz.", "CodiceFiscale", "Sesso", "Riserva", "Scadenza Certificato", "Provincia", "Cognome", "Nome"] 
cols_part_minimal = ["Dors.","Cognome","Nome","UCI ID","Cat.","Società"]
cols_part_essential = ["Dors.","Cognome","Nome","UCI ID","Società"]

st.session_state.header_col = "#1082ce"
st.session_state.com_number = 1



def table_group_km(event, laps=None):

    df = EVENTS_DICT[event]["DLS"]
    df_table = pd.DataFrame({name_cat_short:  list(df.keys()),
                             name_dist_short: [val[0] for val in df.values()],
                             name_laps_short: [val[1] for val in df.values()]})

    df_table = df_table.groupby(name_dist_short).agg({
        name_cat_short: ' '.join,
        name_laps_short: 'first' if laps else 'first'
    }).reset_index()

    if laps is None:
        df_table = df_table[[name_cat_short, name_dist_short]]
        df_table = df_table.style.format({name_cat_short: "{:s}",name_dist_short: "{:.1f}"}).hide(axis="index")
    else:
        df_table = df_table[[name_cat_short, name_dist_short, name_laps_short]]
        df_table = df_table.style.format({name_cat_short: "{:s}",name_dist_short: "{:.1f}",name_laps_short:"{:.0f}"}).hide(axis="index")

    return df_table



def get_sprint_from_text(text, full=False, list_only=False, return_flat=False, do_check=False):
    chack = True

    if text:
        while text[-1] in [",", "-", "/", " "]:
            text = text[:-1]

            if not text:
                break

        text = text.replace(" ", "")

        if not full:
            arr      = [x.split(",") for x in text.split("-")]
            arr      = [[int(y) for y in x] for x in arr]   
            arr_flat = [x for y in arr for x in y]

            # if do_check:
            #     check_dors, check_dors_counts = np.unique(arr_flat, return_counts=True)
            #     check_dors_counts = check_dors_counts > 1
            #     if np.any(check_dors_counts):
            #         dors_err_list = ', '.join(map(str, np.array(check_dors)[check_dors_counts]))
            #         st.error(f"{msg_multiple_nums}: {dors_err_list}")
            #         check = False

            #     check_dors_notin = (~np.isin(check_dors, startlist)) | np.isin(check_dors, elimlist)
            #     if np.any(check_dors_notin):
            #         dors_err_list = ', '.join(map(str, np.array(check_dors)[check_dors_notin]))
            #         st.error(f"{msg_missing_nums}: {dors_err_list}")
            #         check = False


            return arr_flat if return_flat else arr

        else:
            # split in "/" then "-" then "," in one line

        
            arr      = [[y.split(",") for y in x] for x in [x.split("-") for x in text.split("/")]]
            arr      = [[[int(z) for z in y] for y in x] for x in arr]
            arr_flat = [x for y in arr for arr in y for x in arr]

            if list_only:
                return arr_flat

            idx_new_batt, idx_new_team = [], []
            idx_end_batt, idx_end_team = [], []

            # Check no duplicates number with np unique
            # check_dors, check_dors_counts = np.unique(arr_flat, return_counts=True)
            # check_dors_counts = check_dors_counts > 1
            # if np.any(check_dors_counts):
            #     dors_err_list = ', '.join(map(str, np.array(check_dors)[check_dors_counts]))
            #     st.error(f"{msg_multiple_nums}: {dors_err_list}")

            # # Check dorsali non partenti
            # check_dors_notin = ~np.isin(check_dors, startlist)
            # if np.any(check_dors_notin):
            #     dors_err_list = ', '.join(map(str, np.array(check_dors)[check_dors_notin]))
            #     st.error(f"{msg_missing_nums}: {dors_err_list}")

            # else:
            for outer_list in arr:
                idx_new_batt.append(arr_flat.index(outer_list[0][0]))
                idx_end_batt.append(arr_flat.index(outer_list[-1][-1]))
                for inner_list in outer_list:
                    idx_new_team.append(arr_flat.index(inner_list[0]))
                    idx_end_team.append(arr_flat.index(inner_list[-1]))

            return arr_flat, idx_new_batt, idx_new_team, idx_end_batt, idx_end_team
        
    else: 
        if not full:
            return []
        
        else:
            if list_only:
                return []
            else:
                return [],[],[],[],[]


def get_gained_lost():
    col_plus, col_minus = st.sidebar.columns(2)
    with col_plus:
        laps_gained = get_sprint_from_text(st.text_input(name_laps_gained, ""))
    with col_minus:
        laps_lost   = get_sprint_from_text(st.text_input(name_laps_lost, ""))

    return laps_gained, laps_lost

def file_selector(folder_path='.'):
    filenames = os.listdir(folder_path)
    selected_filename = st.selectbox('Select a file', filenames)
    return os.path.join(folder_path, selected_filename)

@st.dialog("Are you sure you want to remove the working dataset?")
def remove_dataset():
    if st.button("Yes, remove it"):
        os.remove(DATASET_WORK)
        st.warning(f"File '{DATASET_WORK}' removed")

def add_comma(key):
    # Get the current value of the text input
    current_text = st.session_state[key]
    # Add a comma if there isn't one already
    if current_text and not current_text.endswith(','):
        st.session_state[key] = current_text + ','

    
def header_logo():
    with open("header/logo.svg", "rb") as f:
        logo = f.read()
    logo_base64 = base64.b64encode(logo).decode()
    st.markdown(
        f'<div class="logo">'
        f'<img src="data:image/svg+xml;base64,{logo_base64}">'
        f'</div>',
        unsafe_allow_html=True
    )

def header_text(text, fontsize=20, comunicato=None):
    if comunicato is not None:
        text = f"Comunicato n. {comunicato} <br>" + text

    st.markdown(f"""<div class="centered-text"><p style="font-size: {fontsize}px; 
                color: {st.session_state.header_col}; font-weight:bold; margin-top:20px; margin-bottom:30px;">{text}</p></div>""", unsafe_allow_html=True)


def table_part_general(df, fontsize=14, hide_index=False):
    df_s = df.style.set_table_styles(
                 [
                     # Tighter row styling
                     {'selector': 'tr', 'props': [('line-height', '0.8'), ('padding', '0 5px'),('font-size', f'{fontsize}pt')]},
                     # Header styling with more padding
                     {'selector': 'thead th', 'props': [('font-size', f'{fontsize}pt')]},
                     # Index styling
                     {'selector': '.row_heading', 'props': [('color', 'gray'), ('font-weight', 'normal'), ('font-size', f'{fontsize}pt'), ('text-align', 'center')]},
                     # Remove borders
                     {'selector': 'table', 'props': [('border', 'none'), ('border-collapse', 'collapse')]},
                     {'selector': 'th', 'props': [('border', 'none')]},
                     {'selector': 'td', 'props': [('border', 'none')]},
                 ]
             )

    df_s = df_s.set_properties(**{'text-align': 'center'})
    df_s = df_s.set_properties(subset=["Cognome","Nome","Società"], **{'text-align': 'left'})
    if hide_index:
        df_s = df_s.hide(axis="index")

    # print(df_s.to_html())
    st.write(df_s.to_html().replace('<table ', '<table class="center"'), unsafe_allow_html=True)


def table_class_group(df, fontsize=14, hide_index=True, last_col_bold=True):
    ncols = len(df.columns)

    df_s = df.style.set_table_styles(
                 [
                     # Tighter row styling
                     {'selector': 'tr', 'props': [('line-height', '0.8'), ('padding', '0 5px'),('font-size', f'{fontsize}pt')]},
                     # Header styling with more padding
                     {'selector': 'thead th', 'props': [('font-size', f'{fontsize}pt'),('overflow','unset')]},
                     {'selector': 'table', 'props': [('border', 'none'), ('border-collapse', 'collapse')]},
                     {'selector': 'th', 'props': [('border', 'none'),('white-space', 'nowrap'),('max-width', '150px'),('overflow','hidden')]},
                     {'selector': 'td', 'props': [('border', 'none'),('white-space', 'nowrap'),('max-width', '150px'),('overflow','hidden')]}, 
                     
                    *[{'selector': f'th.col{i}', 'props': [('max-width', '20px')]} for i in np.arange(6,ncols-2)], 
                    *[{'selector': f'td.col{i}', 'props': [('max-width', '20px')]} for i in np.arange(6,ncols-2)],
                    # column 1 all bold text
                    {'selector': 'th.col1', 'props': [('font-weight', 'bold'),('max-width', '60px')]},
                    {'selector': 'td.col1', 'props': [('font-weight', 'bold')]},
                    # last column bold text
                    {'selector': f'th.col{ncols-1}', 'props': [('font-weight', 'bold')]},
                    {'selector': f'td.col{ncols-1}', 'props': [('font-weight', 'bold')]},
                    # index column blue
                    {'selector': 'th.col0', 'props': [('border-top-style', 'hidden')]},
                    {'selector': 'td.col0', 'props': [('color', f'{st.session_state.header_col}'), ('min-width', '40px'),('padding', '0')]},
                                                                #   ('border-bottom-style', 'hidden'), ('border-top-style', 'hidden')]},  # Making index column bold

                 ]
             )

    df_s = df_s.set_properties(**{'text-align': 'center'})
    df_s = df_s.set_properties(subset=["Cognome","Nome","Società"], **{'text-align': 'left'})
    if hide_index:
        df_s = df_s.hide(axis="index")
    df_html = df_s.to_html().replace('Pos.</th>', ' </th>')

    # 
    st.write(f"<div class='centered-text'>{df_html}</div>", unsafe_allow_html=True)


def table_class_groupEl(df, fontsize=14, hide_index=True, n_left=0):
    ncols = len(df.columns)

    df_s = df.style.set_table_styles(
                 [
                     # Tighter row styling
                     {'selector': 'tr', 'props': [('line-height', '0.8'), ('padding', '0 5px'),('font-size', f'{fontsize}pt')]},
                     # Header styling with more padding
                     {'selector': 'thead th', 'props': [('font-size', f'{fontsize}pt'),('overflow','unset')]},
                     {'selector': 'table', 'props': [('border', 'none'), ('border-collapse', 'collapse')]},
                     {'selector': 'th', 'props': [('border', 'none'),('white-space', 'nowrap'),('max-width', '250px'),('overflow','hidden')]},
                     {'selector': 'td', 'props': [('border', 'none'),('white-space', 'nowrap'),('max-width', '250px'),('overflow','hidden')]}, 
                     
                    *[{'selector': f'th.col{i}', 'props': [('max-width', '20px')]} for i in np.arange(6,ncols-2)], 
                    *[{'selector': f'td.col{i}', 'props': [('max-width', '20px')]} for i in np.arange(6,ncols-2)],
                    # column 1 all bold text
                    {'selector': 'th.col1', 'props': [('font-weight', 'bold'),('max-width', '60px')]},
                    {'selector': 'td.col1', 'props': [('font-weight', 'bold')]},
                    # space to spaate riders still competing
                    {'selector': f'td.row{n_left-1}.col0', 'props': [('padding-bottom', f'50px' if n_left!=0 else "0")]},
                    {'selector': f'td.row{n_left-1}', 'props': [('padding-bottom', f'50px' if n_left!=0 else "0")]},
                    # index column blue
                    {'selector': 'th.col0', 'props': [('color', f'{st.session_state.header_col}'),('font-weight', 'bold')]}, 
                    {'selector': 'td.col0', 'props': [('color', f'{st.session_state.header_col}'), ('min-width', '40px'),('font-weight', 'bold')]},
                                                                #   ('border-bottom-style', 'hidden'), ('border-top-style', 'hidden')]},  # Making index column bold
                 ]
             )

    df_s = df_s.set_properties(**{'text-align': 'center'})
    df_s = df_s.set_properties(subset=["Cognome","Nome","Società"], **{'text-align': 'left'})
    if hide_index:
        df_s = df_s.hide(axis="index")
    df_html = df_s.to_html()#.replace('Pos.</th>', ' </th>')

    # 
    st.write(f"<div class='centered-text'>{df_html}</div>", unsafe_allow_html=True)


def table_class_time(df, fontsize=14, hide_index=True):
    ncols = len(df.columns)

    df_s = df.style.set_table_styles(
                 [
                     # Tighter row styling
                     {'selector': 'tr', 'props': [('line-height', '0.8'), ('padding', '0 5px'),('font-size', f'{fontsize}pt')]},
                     # Header styling with more padding
                     {'selector': 'thead th', 'props': [('font-size', f'{fontsize}pt'),('overflow','unset')]},
                     {'selector': 'table', 'props': [('border', 'none'), ('border-collapse', 'collapse')]},
                     {'selector': 'th', 'props': [('border', 'none'),('white-space', 'nowrap'),('max-width', '150px'),('overflow','hidden')]},
                     {'selector': 'td', 'props': [('border', 'none'),('white-space', 'nowrap'),('max-width', '150px'),('overflow','hidden')]}, 
                     
                    # column 1 all bold text
                    {'selector': 'th.col1', 'props': [('font-weight', 'bold'),('max-width', '60px')]},
                    {'selector': 'td.col1', 'props': [('font-weight', 'bold')]},
                    # last column bold text
                    {'selector': f'th.col{ncols-1}', 'props': [('font-weight', 'bold'),('min-width', '120px')]},
                    {'selector': f'td.col{ncols-1}', 'props': [('font-weight', 'bold'),('min-width', '120px')]},
                    # index column blue
                    {'selector': 'th.col0', 'props': [('border-top-style', 'hidden')]},
                    {'selector': 'td.col0', 'props': [('color', f'{st.session_state.header_col}'), ('min-width', '40px'),('padding', '0')]},
                                                                #   ('border-bottom-style', 'hidden'), ('border-top-style', 'hidden')]},  # Making index column bold

                 ]
             )

    df_s = df_s.set_properties(**{'text-align': 'center'})
    df_s = df_s.set_properties(subset=["Cognome","Nome","Società"], **{'text-align': 'left'})
    if hide_index:
        df_s = df_s.hide(axis="index")
    df_html = df_s.to_html().replace('Pos.</th>', ' </th>')

    # 
    st.write(f"<div class='centered-text'>{df_html}</div>", unsafe_allow_html=True)

def table_part_ins(df, idx_end_batt, idx_end_team, fontsize=14, hide_index=True):
    ncols = len(df.columns)
    nrows = len(df)

    # if same idx for batt and team set pad to 40 else 20
    idx_end = np.unique(np.concatenate([idx_end_batt, idx_end_team]))
    row_pad = [25 if (i in idx_end_batt) and (i in idx_end_team) else 25 for i in idx_end]


    df_s = df.style.set_table_styles(
                 [
                     # Tighter row styling
                     {'selector': 'tr', 'props': [('line-height', '0.8'), ('padding', '0 5px'),('font-size', f'{fontsize}pt')]},
                     # Header styling with more padding
                     {'selector': 'thead th', 'props': [('font-size', f'{fontsize}pt'),('overflow','unset')]},
                    #  {'selector': 'table', 'props': [('border', 'none'), ('border-collapse', 'collapse')]},
                     {'selector': 'th', 'props': [('border', 'none'),('white-space', 'nowrap'),('max-width', '150px'),('overflow','hidden')]},
                     {'selector': 'td', 'props': [('border', 'none'),('white-space', 'nowrap'),('max-width', '150px'),('overflow','hidden')]}, 
                     
                    # column 1 all bold text
                    {'selector': 'th.col1', 'props': [('font-weight', 'bold'),('max-width', '60px')]},
                    {'selector': 'td.col1', 'props': [('font-weight', 'bold')]},
                    # last column bold text
                    {'selector': f'th.col{ncols-1}', 'props': [('min-width', '220px')]},
                    {'selector': f'td.col{ncols-1}', 'props': [('min-width', '220px')]},

                    *[{'selector': f'th.row{idx_end[i]}', 'props': [('padding-bottom', f'{row_pad[i]}px')]} for i in range(len(idx_end))],
                    *[{'selector': f'td.row{idx_end[i]}', 'props': [('padding-bottom', f'{row_pad[i]}px')]} for i in range(len(idx_end))],

                    *[{'selector': f'td.row{i}', 'props': [('border-bottom-style', 'hidden')]} for i in range(nrows) if i not in idx_end_batt],
                    {'selector': f'td.row0', 'props': [('padding-top', '10px')]},

                    # index column blue
                    {'selector': 'th.col0', 'props': [('color', f'{st.session_state.header_col}')]},
                    {'selector': 'td.col0', 'props': [('color', f'{st.session_state.header_col}'), ('min-width', '40px'),('font-weight', 'bold')]},
                                                                #   ('border-bottom-style', 'hidden'), ('border-top-style', 'hidden')]},  # Making index column bold

                 ]
             )

    df_s = df_s.set_properties(**{'text-align': 'center'})
    df_s = df_s.set_properties(subset=["Cognome","Nome","Società"], **{'text-align': 'left'})
    if hide_index:
        df_s = df_s.hide(axis="index")
    df_html = df_s.to_html()#.replace('Pos.</th>', ' </th>')

    # 
    st.write(f"<div class='centered-text'>{df_html}</div>", unsafe_allow_html=True)

# def table_class_ins(df, fontsize=14, hide_index=True):

def page_formatter():
    page_layout_part_general()

    st.sidebar.divider()
    col_fhead, col_ftable = st.sidebar.columns(2)
    with col_fhead:
        fontsize_head = st.number_input("Font titolo", min_value=20., value=25., max_value=99., format="%.1f", step=1.)
    with col_ftable: 
        fontsize_table = st.number_input("Font tabella", min_value=6., value=12., max_value=20., format="%.1f", step=0.5)

    return fontsize_head, fontsize_table



def group_race(df_race, event, n_sprint):

    df_race.insert(0, name_pos_short, "")
    df_race.insert(len(df_race.columns), name_last_sprint, "")
    for s in range(n_sprint):
        df_race[f"{s+1}"] = 0

    startlist         = np.array(df_race["Dors."]).astype(int)
    sprintlist_txt    = st.sidebar.text_input(name_group_race_sprint_input[0], "", help=name_group_race_sprint_input[1])
    # sprintlist_txt = st.sidebar.text_input(name_group_race_sprint_input[0], value=st.session_state.get(glob_class_input, ""), 
    #                                        key=glob_class_input, help=name_group_race_sprint_input[1])
    sprintlist        = get_sprint_from_text(sprintlist_txt)
    n_sprintlist      = len(sprintlist)

    # Check number of sprint
    check_n_sprint(n_in=n_sprintlist, n_max=n_sprint)

    dns_list, dnf_list, dsq_list = get_dns_dnf_dsq()
    laps_gained, laps_lost       = get_gained_lost()
    gained_n, gained_c           = np.unique(laps_gained, return_counts=True)
    lost_u, lost_c               = np.unique(laps_lost, return_counts=True)

    # Assign sprint points for each sprint
    for i, sprint in enumerate(sprintlist):

        # Check no duplicates number with np unique
        num_u, num_c = np.unique(sprint, return_counts=True)
        check_num_c = num_c > 1
        if np.any(check_num_c):
            dors_err_list = ', '.join(map(str, np.array(num_u)[check_num_c]))
            st.error(f"{msg_multiple_nums}: {dors_err_list} (sprint {i+1})")

        for n in sprint:
            check_n_rider(startlist, n, i)
            

        if event == TempR:
            df_race.loc[df_race["Dors."]==sprint[0],f"{i+1}"] = 1

        if event == PtR:
            if check_sprint_len(sprint, i, startlist):
                idx_dors = [df_race[df_race["Dors."] == v].index[0] for v in sprint[:4]]
                df_race.loc[idx_dors, f"{i+1}"] = [5, 3, 2, 1] if i < n_sprint-1 else [10, 6, 4, 2]

        # if event == "Scratch":
        #     idx_dors = [df_race[df_race["Dors."] == v].index[0] for v in last_sprint[:4]]
        #     df_race.loc[idx_dors, f"{s+1}"] = [10, 6, 4, 2]

        # Assign last sprint position
        df_race[name_last_sprint] = df_race["Dors."].apply(lambda x: sprint.index(x) if x in sprint else len(sprint))

    # Assign gained/lost laps
    df_race[name_laps_short] = 0
    for n, c in zip(gained_n, gained_c):
        if check_n_rider(startlist, n):
            df_race[name_laps_short][df_race["Dors."]==n] += 20*c

    for n, c in zip(lost_u, lost_c):
        if check_n_rider(startlist, n):
            df_race[name_laps_short][df_race["Dors."]==n] += (-20)*c

    # Compute total points
    df_race[name_tot_short] = np.sum(df_race[[str(i+1) for i in range(n_sprint)]], axis=1) + df_race[name_laps_short]

    # Assign DNS, DNF, DSQ in final ranking
    for i, dnf in enumerate(dnf_list):
        if check_n_rider(startlist, dnf):
            idx = df_race["Dors."]==dnf
            df_race.loc[idx, name_pos_short]    = "DNF"
            df_race.loc[idx, name_tot_short]    = 0
            df_race.loc[idx, name_last_sprint]  = 1000+i
        
    for i, dns in enumerate(dns_list):
        if check_n_rider(startlist, dns):
            idx = df_race["Dors."]==dns
            df_race.loc[idx, name_pos_short]    = "DNS"
            df_race.loc[idx, name_tot_short]    = 0
            df_race.loc[idx, name_last_sprint]  = 2000+i
            
    for i, dsq in enumerate(dsq_list):
        if check_n_rider(startlist, dsq):
            idx = df_race["Dors."]==dsq
            df_race.loc[idx, name_pos_short]    = "DSQ"
            df_race.loc[idx, name_tot_short]    = 0
            df_race.loc[idx, name_last_sprint]  = 3000+i


    len_class = len(startlist)-len(dnf_list)-len(dns_list)-len(dsq_list)

    df_race = df_race.sort_values(by=[name_tot_short, name_last_sprint], ascending=[False, True])
    df_race = df_race.drop(columns=[name_last_sprint])
    df_race[name_pos_short][:len_class] = [f"{i}°" for i in range(1, len_class+1)]

    # Estetica
    for i in range(n_sprint):
        df_race[f"{i+1}"] = np.where(df_race[f"{i+1}"]!=0, df_race[f"{i+1}"], "")
    df_race[name_tot_short]  = np.where(df_race[name_tot_short]!=0, df_race[name_tot_short], "")
    df_race[name_laps_short] = df_race[name_laps_short].apply(lambda x: f"{x:+d}")
    df_race[name_laps_short] = np.where(df_race[name_laps_short]!="+0", df_race[name_laps_short], "")

    if event == "Scratch":
        df_race = df_race.drop(columns=[str(i+1) for i in range(n_sprint)])

    return df_race


def elimination_race(df_race, event, cat):

    df_race.insert(0, name_pos_short, 0)

    glob_class_input = 'class_input'+event.replace(" ", "")+cat
    
    startlist    = np.array(df_race["Dors."]).astype(int)
    # elimlist_txt = st.sidebar.text_input(name_group_race_el_input, value=st.session_state.get(glob_class_input, ""), key=glob_class_input)
    elimlist_txt = st.sidebar.text_input(name_group_race_el_input, value="")
    elimlist     = np.array(get_sprint_from_text(elimlist_txt)).flatten()
    n_startlist  = len(startlist)
    n_elimlist   = len(elimlist)

    # Check number of sprint
    check_n_sprint(n_in=n_elimlist, n_max=n_startlist)

    dns_list, dnf_list, dsq_list = get_dns_dnf_dsq()

    # Check no duplicates number with np unique
    num_u, num_c = np.unique(elimlist, return_counts=True)
    check_num_c = num_c > 1
    if np.any(check_num_c):
        dors_err_list = ', '.join(map(str, np.array(num_u)[check_num_c]))
        st.error(f"{msg_multiple_nums}: {dors_err_list}")

    n_out   = len(dnf_list) + len(dns_list) + len(dsq_list)
    n_class = n_elimlist - n_out
    n_left  = n_startlist - n_elimlist - n_out

    for i, elim in enumerate(elimlist):
        if check_n_rider(startlist, elim):
            df_race.loc[df_race["Dors."]==elim, name_pos_short]  = n_startlist-i

    for i, dnf in enumerate(dnf_list):
        if check_n_rider(startlist, dnf) & (check_n_rider(elimlist, dnf, is_in=True)):
            df_race.loc[df_race["Dors."] == dnf, name_pos_short] = 1000 + i
        
    for i, dns in enumerate(dns_list):
        if check_n_rider(startlist, dns) & (check_n_rider(elimlist, dns, is_in=True)):
            df_race.loc[df_race["Dors."] == dns, name_pos_short] = 2000 + i
        
    for i, dsq in enumerate(dsq_list):
        if check_n_rider(startlist, dsq) & (check_n_rider(elimlist, dsq, is_in=True)):
            df_race.loc[df_race["Dors."] == dsq, name_pos_short] = 3000 + i

    df_race = df_race.sort_values(by=[name_pos_short]).reset_index(drop=True)
    df_race.index += 1

    do_dnf   = df_race[name_pos_short]>=1000
    do_dns   = df_race[name_pos_short]>=2000
    do_dsq   = df_race[name_pos_short]>=3000

    df_race[name_pos_short] -= n_out
    df_race.loc[0:n_left, name_pos_short] = ""
    df_race.loc[n_left+1:n_left+1+n_class, name_pos_short] = df_race.loc[n_left+1:n_left+1+n_class, name_pos_short].apply(lambda x: f"{x}°")
    df_race.loc[do_dnf, name_pos_short]   = "DNF"
    df_race.loc[do_dns, name_pos_short]   = "DNS"
    df_race.loc[do_dsq, name_pos_short]   = "DSQ"

    df_race.loc[df_race[name_pos_short]==0, name_pos_short] = ""

    return df_race, n_left


def individual_sprint_race(df_race):

        
    df_race.insert(0, name_pos_short, "")
    df_race.insert(len(df_race.columns), name_time, None)

    startlist   = np.array(df_race["Dors."]).astype(int)

    # Insert times
    st.sidebar.markdown(name_time_input)
    with st.sidebar.container(height=200):
        df_race=st.data_editor(df_race, use_container_width=True, column_order=["Dors.",name_time], disabled=["Dors."], hide_index=True,)

    dns_list, dnf_list, dsq_list = get_dns_dnf_dsq()

    for i, dnf in enumerate(dnf_list):
        if check_n_rider(startlist, dnf):
            df_race.loc[df_race["Dors."] == dnf, name_time]      = f"59:51.{i:03d}"
            df_race.loc[df_race["Dors."] == dnf, name_pos_short] = "DNF"
        
    for i, dns in enumerate(dns_list):
        if check_n_rider(startlist, dns):
            df_race.loc[df_race["Dors."] == dns, name_time]      = f"59:52.{i:03d}"
            df_race.loc[df_race["Dors."] == dns, name_pos_short] = "DNS"

        
    for i, dsq in enumerate(dsq_list):
        if check_n_rider(startlist, dsq):
            df_race.loc[df_race["Dors."] == dsq, name_time]      = f"59:53.{i:03d}"
            df_race.loc[df_race["Dors."] == dsq, name_pos_short] = "DSQ"


    # Formatta times
    df_race[name_time].replace('', pd.NA, inplace=True)
    df_race[name_time] = pd.to_datetime(df_race[name_time].str.replace(".",":"), format='%M:%S:%f')
    hide_times = np.logical_or(df_race[name_time] >= pd.to_datetime("59:50:000", format='%M:%S:%f'), pd.isna(df_race[name_time]))

    # Sort times
    df_race = df_race.sort_values(by=name_time, ascending=True)

    # Assign ranking positions
    len_class = len(startlist)-len(dnf_list)-len(dns_list)-len(dsq_list)-sum(df_race[name_time].isna())
    df_race["Pos."][:len_class] = [f"{i}°" for i in range(1, len_class+1)]

    # Estetica
    df_race[name_time] = df_race[name_time].apply(lambda t: f"{t.second:02}.{t.microsecond // 1000:03}" \
                                                            if not pd.isna(t) and not hide_times[df_race.index[df_race[name_time] == t][0]] and t.minute == 0 else \
                                                            f"{t.minute:02}:{t.second:02}.{t.microsecond // 1000:03}" \
                                                            if not pd.isna(t) and not hide_times[df_race.index[df_race[name_time] == t][0]] else " ")

    return df_race



def pursuit_race(df_race, event, cat, do_stage, do_class):
    
    df_race.insert(0, name_pos_short, "")
    startlist   = np.array(df_race["Dors."]).astype(int)

    glob_sort_name = 'sorting_order_'+event.replace(" ", "")+cat


    # Startlist section
    if not do_class:

        st.session_state[glob_sort_name] = st.sidebar.text_input(name_pursuit_input, value=st.session_state.get(glob_sort_name, ""), help="e.g., `1/2-3/4-5/6-7`")
        dors_sorted_flat, idx_new_batt, idx_new_team, idx_end_batt, idx_end_team = get_sprint_from_text(st.session_state[glob_sort_name], full=True)

        # Sort riders as the input
        df_race['sort_key'] = df_race['Dors.'].apply(lambda x: dors_sorted_flat.index(x) if x in dors_sorted_flat else len(dors_sorted_flat))
        df_race = df_race.sort_values(by=['sort_key', 'Dors.']).drop(columns='sort_key').reset_index(drop=True)

        # for each idx_new_batt insert "Batt." 1, 2, 3...
        df_race["Pos."][idx_new_batt] = [f"{i+1}" for i in range(len(idx_new_batt))]
        df_race = df_race.rename(columns={name_pos_short:name_batt_short})
          
        return df_race, idx_end_batt, idx_end_team

    # Ranking section
    else:
        df_race.insert(len(df_race.columns), "Tempo", None)


        # If present in qualification apply sort
        if st.session_state[glob_sort_name]:
            dors_sorted_flat = get_sprint_from_text(st.session_state[glob_sort_name], full=True, list_only=True)
            df_race['sort_key'] = df_race['Dors.'].apply(lambda x: dors_sorted_flat.index(x) if x in dors_sorted_flat else len(dors_sorted_flat))
            df_race = df_race.sort_values(by=['sort_key', 'Dors.']).drop(columns='sort_key').reset_index(drop=True)


        st.sidebar.markdown("**Inserisci tempi** (`mm:ss.000`)")
        with st.sidebar.container(height=200):
            df_race=st.data_editor(df_race, use_container_width=True, column_order=["Dors.","Tempo"], disabled=["Dors."], hide_index=True,)

        col_dnf, col_dns, col_dsq = st.sidebar.columns(3)
        with col_dnf:
            dns_txt = st.text_input("**DNS**", "")
        with col_dns:
            dnf_txt = st.text_input("**DNF**", "")
        with col_dsq:
            dsq_txt = st.text_input("**DSQ**", "")


        # Assegna posizione in classifica, DNS, DNF, DSQ
        dns_list        = np.array(get_sprint_from_text(dns_txt)).flatten()
        dnf_list        = np.array(get_sprint_from_text(dnf_txt)).flatten()
        dsq_list        = np.array(get_sprint_from_text(dsq_txt)).flatten()

        for i in range(len(dnf_list)):
            if dnf_list[i] not in startlist:
                st.warning(f"Dorsale {dnf_list[i]} non presente tra i partenti. Rimuovilo.")
            else:
                idx = df_race["Dors."]==dnf_list[i]
                df_race["Pos."][idx] = "DNF"
                df_race["Tempo"][idx] = f"59:51.{i:03d}"

        for i in range(len(dns_list)):
            if dns_list[i] not in startlist:
                st.warning(f"Dorsale {dns_list[i]} non presente tra i partenti. Rimuovilo.")
            else:
                idx = df_race["Dors."]==dns_list[i]
                df_race["Pos."][idx] = "DNS"
                df_race["Tempo"][idx] = f"59:52.{i:03d}"

        for i in range(len(dsq_list)):
            if dsq_list[i] not in startlist:
                st.warning(f"Dorsale {dsq_list[i]} non presente tra i partenti. Rimuovilo.")
            else:
                idx = df_race["Dors."]==dsq_list[i]
                df_race["Pos."][idx] = "DSQ"
                df_race["Tempo"][idx] = f"59:53.{i:03d}"


        # Formatta tempi
        df_race['Tempo'].replace('', pd.NA, inplace=True)
        df_race['Tempo'] = pd.to_datetime(df_race['Tempo'].str.replace(".",":"), format='%M:%S:%f')
        hide_times = np.logical_or(df_race['Tempo'] >= pd.to_datetime("59:50:000", format='%M:%S:%f'), pd.isna(df_race['Tempo']))

        # Ordina tempi
        df_race = df_race.sort_values(by='Tempo', ascending=True)

        # Assegna posizione in classifica
        len_class = len(startlist)-len(dnf_list)-len(dns_list)-len(dsq_list)-sum(df_race['Tempo'].isna())
        df_race["Pos."][:len_class] = [f"{i}°" for i in range(1, len_class+1)]

        # Estetica


        df_race['Tempo'] = df_race['Tempo'].apply(lambda t: f"{t.second:02}.{t.microsecond // 1000:03}" \
                                                            if not pd.isna(t) and not hide_times[df_race.index[df_race['Tempo'] == t][0]] and t.minute == 0 else \
                                                            f"{t.minute:02}:{t.second:02}.{t.microsecond // 1000:03}" \
                                                            if not pd.isna(t) and not hide_times[df_race.index[df_race['Tempo'] == t][0]] else " ")

        

        st.sidebar.divider()
        col_fhead, col_ftable = st.sidebar.columns(2)
        with col_fhead:
            fontsize_head = st.number_input("Font titolo", min_value=30., max_value=99., format="%.1f", step=1.)
        with col_ftable: 
            fontsize_table = st.number_input("Font tabella", min_value=6., value=12., max_value=14., format="%.1f", step=0.5)

        page_layout_part_general()
        header_text(txt, fontsize_head, com)

        if df_race is not None:
            df_race = df_race.reset_index(drop=True)
            df_race.index += 1
            table_class_time(df_race, fontsize=fontsize_table)



    return df_race, label_class, label_stage



def page_layout_part_general():
    css = """
    .main div[data-testid="stVerticalBlock"] {
        gap: 0 !important;
    }
        
    table.center {
        margin-left:auto; 
        margin-right:auto;
    }

    .centered-text {
        display: flex;
        justify-content: center;
        align-items: center;
        text-align: center;
        width: 100%;
    }
    # .st-emotion-cache-79wnr2 > * {
    #     margin-top: 0 !important;
    # }
    .st-emotion-cache-1ujs6c {
        gap: 0;
    }

    .logo {
        display: flex;
        justify-content: center;
        padding: 0;
        margin-top: 0 !important;
        margin-bottom: 10px;
    }

    .logo img {
        width: 270px;
        margin: 0;  /* Ensure the image has no margins */
        # position: relative;  /* Allow positioning adjustments */
    }

    .hover-container {
        display: flex; /* Allows the container to wrap around the icon */
        flex-direction: row-reverse;
        margin-top: -85px;
    }

    .hover-box {
        visibility: hidden; /* Initially hidden */
        width: 290px; /* Width of the hover box */
        background-color: white; /* Background color of the hover box */
        border: 1px solid #ddd; /* Border styling */
        box-shadow: 0px 0px 10px rgba(0,0,0,0.1); /* Shadow effect */
        border-radius: 10px; /* Rounded corners */
        padding: 10px; /* Padding inside the hover box */
        position: absolute; /* Positioning the hover box */
        z-index: 10; /* Ensures it appears above other elements */
        top: -55px; /* Adjust this value to position it correctly */
        right: 0px; /* Align with the left edge of the icon */
    }

    .hover-container:hover .hover-box {
        visibility: visible; /* Show the hover box on hover */
    }

    .hover-box table {
        width: 100%; /* Full width for the table */
        border-collapse: collapse; /* Collapse borders */
        font-size: 15px; /* Font size for the table */
    }

    .hover-box th, .hover-box td {
        padding: 1px; /* Padding for table cells */
    }

    
    @media print {
        section[data-testid="stSidebar"], section[data-testid="collapsedControl"], .st-emotion-cache-19u4bdk{
            display: none;
        }
        .st-emotion-cache-qu19o6 {
            gap: 0 !important;
        }
        .st-emotion-cache-1jicfl2 {
            padding: 0;
        }
        table {
            width: 100%; /* Ensure table takes full width */
            border-collapse: collapse; /* Collapse borders for cleaner look */
            margin: 0; /* Remove margin to avoid extra space */
            word-wrap: break-word; 
        }
        @page {
            size: auto;
            margin: 1cm 1.5cm 1cm 1.4cm !important;
        }


        # @page:first {
        #     margin-top: 0 !important;
        # }

        .centered-text {
            display: flex;
            justify-content: center;
            align-items: center;
            text-align: center;
            margin: 0;
            padding: 0;
            width: auto; /* Use auto to fit the content */
            max-width: 100%; /* Ensure it doesn't exceed page width */
        }
        .page-break {
            page-break-before: always; /* Page break before the element with this class */
        }
        .footer {
            display: block;
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            text-align: center;
            font-size: 16px; /* Adjust font size as needed */
            padding: 10px 0; /* Add padding */
            # border-top: 1px solid #ddd; /* Optional: border for separation */
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .footer .left { text-align: left; flex: 1;}
        .footer .center { text-align: center; flex: 1;}
        .footer .right { text-align: right; flex: 1;}

        # * {
        #     box-sizing: content-box !important;
        # }
    }

    
    @media screen {
        .footer {
            display: none;
    }

    """

    st.markdown(f'<style>{css}</style>', unsafe_allow_html=True)

    footer_html = f"""
    <div class="footer">
        <div class="left">Per la giuria: <i>Nicola Borghi</i></div>
        <div class="right" id="print-date">{datetime.today().strftime("%d/%m/%Y")}</div>
    </div>"""

    st.markdown(footer_html, unsafe_allow_html=True)

                    
                

    # Hide sidebar when printing
    # st.markdown(
    #     """
    #     <script>
    #     window.addEventListener('beforeprint', function() {
    #         var sidebar = document.querySelector('section[data-testid="stSidebar"]');
    #         if (sidebar) {
    #             sidebar.setAttribute('aria-expanded', 'false');
    #         }
    #     });
    #     </script>
        
    #     <style>
    #     @media print {
    #         section[data-testid="stSidebar"] {
    #             display: none;  /* Optionally hide the sidebar completely */
    #         }
    #     }
    #     </style>
    #     """,
    #     unsafe_allow_html=True,
    # )

###############################################
############################################### Load & Clean Data
###############################################


def load_clean_dataset(filename):
    dtype_iscr_ksport = {"IdGara":int, "NomeGara":"U100",
                        "DorsaleNumero":pd.Int64Dtype(), "NomeTesserato":"U100", "CodiceFCI":"U7", "Categoria":"U5", "CodiceUci":"U100",
                        "Nazionalità":"U3", "DataNascita":"U10",
                        "NomeSocieta":"U100",  "CodiceSocieta":"U100", 
                        "CodiceFiscale":"U16", "Sesso":"U1", "Note": "U100",
                        "Cognome":"U100", "Nome":"U100", "Riserva":"U2", "Scadenza Certificato":"U100", "Provincia":"U2"}

    # Define columns for various operations
    cols_rename_ksport = {"DorsaleNumero":"Dors.", "Categoria":"Cat.", "CodiceUci":"UCI ID", "Nazionalità":"Naz.", "DataNascita":"Nato", 
                          "NomeSocieta":"Società", "CodiceSocieta":"Cod. Soc."}

    dtype_iscr         = {"IdGara":int, "NomeGara":"U100",
                        "Dors.":pd.Int64Dtype(), "NomeTesserato":"U100", "CodiceFCI":"U7", "Cat.":"U5", "UCI ID":"U100",
                        "Naz.":"U3", "Nato":"U10",
                        "Società":"U100",  "Cod. Soc.":"U100", 
                        "CodiceFiscale":"U16", "Sesso":"U1", "Note": "U100",
                        "Cognome":"U100", "Nome":"U100", "Riserva":"U2", "Scadenza Certificato":"U100", "Provincia":"U2"}

    # New dictionary with key substituted by  cols_rename_ksport
    dtype_iscr = {cols_rename_ksport.get(k, k):v for k,v in dtype_iscr_ksport.items()}

    # Add helper column for NP
    dtype_iscr.update({"NP":bool})

    # Add helper columns with events if values is 1
    dtype_iscr.update({k:bool for k in EVENTS})

    # Madison is int to assign couples
    if "Madison" in dtype_iscr:
        dtype_iscr["Madison"] = pd.Int8Dtype()

    # Load & clean original dataset from ksport Iscritti_XXX.xls
    if not os.path.exists(DATASET_WORK):
        print("aaaa")

        df = pd.read_excel(filename, dtype=dtype_iscr_ksport)
        df = df.rename(columns=cols_rename_ksport)

        # ifnot exist columns in dtype_iscr create in the dataset
        for col, dtype in dtype_iscr.items():
            if col not in df.columns:
                if col == "Madison":
                    df[col] = None
                else:
                    df[col] = False

        df.to_excel(DATASET_WORK, sheet_name='Sheet1', engine='openpyxl', index=False)


    # Reload
    df = pd.read_excel(DATASET_WORK, dtype=dtype_iscr)
    IdGara = df["IdGara"][0]
    NomeGara = df["NomeGara"][0]
    df.index +=1 # Start from 1

    CATEGORIE = np.atleast_1d(np.unique(df["Cat."]))

    # sort array according to sort_categorie
    CATEGORIE = np.array(sorted(CATEGORIE, key=lambda x: sort_categories.index(x)))


    # df_part = df[cols_part]

    return df, IdGara, NomeGara, CATEGORIE


df, IdGara, NomeGara, CATEGORIE = load_clean_dataset(DATASET)


###############################################
############################################### Sidebar/Page
###############################################

PAGES = ["Gare", "Impostazioni", "Verifica", "Partenti","Classsifiche"]



# st.sidebar.header("Pista 100 🌀")

st.logo("header/logo_pista.svg")
page = st.sidebar.selectbox("", PAGES)

if page == "Impostazioni":
    st.session_state.header_col = st.color_picker("Header color", "#1082ce", key="head_color")

if page == "Verifica":
    st.sidebar.divider()
    st.sidebar.text(f"Gara: {NomeGara}")
    st.sidebar.text(f"ID: {IdGara}")
    st.sidebar.text("Categorie: "+" ".join(CATEGORIE))
    st.sidebar.divider()
    page_layout_part_general()


    # with st.sidebar.expander("Add or Modify .XXX columns"):
    #     discipline = st.text_input("Enter the discipline code (e.g., BMX, CX, ROA)")
    #     if discipline:
    #         column_name = f".{discipline}"
    #         if column_name not in df.columns:
    #             df[column_name] = False  # Initialize with False if column does not exist
    #             st.success(f"Column {column_name} created")
    #         else:
    #             st.warning(f"Column {column_name} already exists")

    # # Filter columns to only include those that start with a period
    # spec_columns = [col for col in df.columns if col.startswith('.')]



    default_cols_to_show = [col for col in df.columns if col not in default_cols_to_hide]

    # Move UCI ID befote Nato
    default_cols_to_show.remove("UCI ID")
    default_cols_to_show.insert(default_cols_to_show.index("Cat."), "UCI ID")



    # with st.sidebar.expander("Nascondi colonne"):
        # columns_to_show = st.multiselect("Colonne:", df.columns, default=default_cols_to_show)


    columns_to_show = st_tags_sidebar(
        label='Colonne visualizzate:',
        text='Aggiungi colonne',
        value=default_cols_to_show,
        suggestions=df.columns,
        maxtags = 99,
        key=None)
    
    # if columns_to_show does not exist in df.columns, add it as boolean
    for col in columns_to_show:
        if col not in df.columns:
            df[col] = False

    edited_df = st.data_editor(df, column_order=columns_to_show)

    st.sidebar.divider()

    # Save button to store changes
    if st.sidebar.button("Aggiorna Dataset", type="primary"):

        # Update the original DataFrame with the edited DataFrame
        for col in edited_df.columns:
            df[col] = edited_df[col]
    
        # Save the edited DataFrame back to the same Excel file
        df.to_excel(DATASET_WORK, sheet_name='Sheet1', engine='openpyxl', index=False)
        st.success(f"Changes saved to '{DATASET_WORK}'")

    if st.sidebar.button("Rimuovi Dataset"):
        # Ask if sure with dialog box to
        remove_dataset()

elif page == "Partenti":
    page_layout_part_general()
    

    st.sidebar.divider()
    st.sidebar.subheader("Opzioni")
    do_divide = st.sidebar.selectbox("Mostra:",("Tutti", "Per categoria", "Per disciplina"),)

    col1, col2, col3 = st.sidebar.columns(3)

    with col1:
        add_disciplines = st.checkbox("Discipline")
        if do_divide is not "Tutti":
            do_break = st.checkbox("Separa")
    with col2:
        add_NP = st.checkbox("NP")
    with col3:
        do_no_logo = st.checkbox("No logo")

    if not do_no_logo:
        header_logo()

    col11, col21 = st.sidebar.columns(2)
    with col11:
        fontsize_head = st.number_input("Font titolo", min_value=30., max_value=99., format="%.1f", step=1.)
    with col21: 
        fontsize_table = st.number_input("Font tabella", min_value=12., max_value=14., format="%.1f", step=0.5)
                 
            
    if add_NP:
        df["Dors."] = np.where(df["NP"], "NP", df["Dors."])
    else:
        df = df[df["NP"]==False]

    cols_part_disc = cols_part_minimal + [k for k in EVENTS]


    if add_disciplines:
        df_part = df[cols_part_disc]

        for col in EVENTS:
            if df[col].dtype == bool:
                _col = np.where(df_part[col], "x", "")
                df_part.drop(columns=[col])
                df_part[col] = _col

        df_part = df_part.rename(columns={k: v["shortname"] for k, v in EVENTS_DICT.items()})


    else:
        df_part = df[cols_part_minimal]
        df_part = df_part.reset_index(drop=True)
        df_part.index += 1
    

    if do_divide=="Per categoria":

        for i in range(len(CATEGORIE)):
            
            if do_break and (i>0):
                st.markdown('<div class="page-break"></div>', unsafe_allow_html=True)
                if not do_no_logo:
                    header_logo()

            df_part_cat = df_part[df_part["Cat."]==CATEGORIE[i]]
            df_part_cat = df_part_cat.reset_index(drop=True)
            df_part_cat.index += 1

            text = f"Partenti - {CATEGORIE[i]} (tot: { np.sum( (~df['NP'])&(df['Cat.']==CATEGORIE[i]) )})"
            header_text(text, fontsize_head, comunicato=i+1)
            table_part_general(df_part_cat, fontsize=fontsize_table)

    elif do_divide=="Per disciplina":
        
        for i in range(len(EVENTS)):
            if do_break and (i>0):
                st.markdown('<div class="page-break"></div>', unsafe_allow_html=True)
                if not do_no_logo:
                    header_logo()

            df_part_disc = df_part[df_part[EVENTS[i]]]
            df_part_disc = df_part_disc.reset_index(drop=True)
            df_part_disc.index += 1

            text = f"Partenti - {EVENTS[i]} (tot: { np.sum( (~df['NP'])&(df[EVENTS[i]]) )})"
            header_text(text, fontsize_head)
            table_part_general(df_part_disc, fontsize=fontsize_table)
    
    elif do_divide=="Tutti":

        text = f"Partenti (tot: {np.sum(~df['NP'])})"
        header_text(text, fontsize_head)
        table_part_general(df_part, fontsize=fontsize_table)



elif page == "Gare":

    col_event, col_cat = st.sidebar.columns([2,1])
    with col_event:
        event = st.selectbox(name_event, EVENTS)
    with col_cat:
        cat = st.selectbox(name_cat, np.unique(df["Cat."][df[event]==True]))

        if not cat:
         st.stop()

    # Select dataset of riders doing disc of "Cat."==cat
    mask = (df[event]) & (df["Cat."]==cat)
    df_race = df[mask]
    df_race = df_race.reset_index(drop=True)
    df_race.index += 1

    table_html = table_group_km(event, TRACK_LEN).to_html(index=False, border=0)

    kind = EVENTS_DICT[event]["kind"]

    n_laps = EVENTS_DICT[event]["DLS"][cat][1]
    n_sprint = int(EVENTS_DICT[event]["DLS"][cat][2])

    if event == ElR:
        n_laps = len(df_race) * (3 if TRACK_LEN < 0.2 else 2 if TRACK_LEN < 0.33333 else 1)

    if kind in ["group", "groupEl"]:
        fmt_laps = int                
    else:
        fmt_laps = float
        
    # Com. number, laps, and sprints input
    col_com, col_giri, col_sprint = st.sidebar.columns(3)
    with col_com:
        st.session_state.com_number = st.number_input("Comunicato", value=st.session_state.com_number )
        com = st.session_state.com_number

    with col_giri:
        # If qualifications change
        n_laps = st.number_input("Numero giri", min_value=fmt_laps(1.), step=fmt_laps(1.), value=fmt_laps(n_laps))
    with col_sprint:
        if n_sprint == 0:
            n_sprint = st.number_input("Numero sprint", min_value=0, step=1, value=0, disabled=True)
        else:
            n_sprint = st.number_input("Numero sprint", min_value=1, step=1, value=n_sprint)

    if event not in [ElR]:
        st.sidebar.html(f'<div class="hover-container"><span>📜</span><div class="hover-box">{table_html}</div></div>')


    if kind=="group":
        df_race = df_race[cols_part_essential]

        df_race = group_race(df_race, event, n_sprint)

        st.sidebar.divider()

        title, decision = get_title_decision(name_class, event, cat, n_laps, n_sprint)

        col_fhead, col_ftable = st.sidebar.columns(2)
        with col_fhead:
            fontsize_head = st.number_input("Font titolo", min_value=30., max_value=99., format="%.1f", step=1.)
        with col_ftable: 
            fontsize_table = st.number_input("Font tabella", min_value=6., value=12., max_value=14., format="%.1f", step=0.5)

        page_layout_part_general()
        header_text(title, fontsize_head, com)

        df_race = df_race.reset_index(drop=True)
        df_race.index += 1

        table_class_group(df_race, fontsize=fontsize_table)

        if decision:
            st.markdown(f"<br><br><br>", unsafe_allow_html=True)
            textsplit = decision.splitlines()
            for x in textsplit:
                st.markdown(f"<div style='text-align: left;'><b>{x}</b></div>", unsafe_allow_html=True)

    elif kind=="groupEl":
        df_race = df_race[cols_part_essential]

        df_race, n_left = elimination_race(df_race, event, cat)

        title, decision = get_title_decision(name_class, event, cat, n_laps, n_sprint)

        col_fhead, col_ftable = st.sidebar.columns(2)
        with col_fhead:
            fontsize_head = st.number_input("Font titolo", min_value=30., max_value=99., format="%.1f", step=1.)
        with col_ftable: 
            fontsize_table = st.number_input("Font tabella", min_value=6., value=12., max_value=14., format="%.1f", step=0.5)

        page_layout_part_general()
        header_text(title, fontsize_head, com)

        df_race = df_race.reset_index(drop=True)
        df_race.index += 1

        table_class_groupEl(df_race, fontsize=fontsize_table, n_left=n_left)

        if decision:
            st.markdown(f"<br><br><br>", unsafe_allow_html=True)
            textsplit = decision.splitlines()
            for x in textsplit:
                st.markdown(f"<div style='text-align: left;'><b>{x}</b></div>", unsafe_allow_html=True)


    elif kind=="timeSprint":

        df_race = df_race[cols_part_essential]
        df_race = individual_sprint_race(df_race)

        title, decision = get_title_decision(name_class, event, cat, n_laps, n_sprint)
        col_fhead, col_ftable = st.sidebar.columns(2)
        with col_fhead:
            fontsize_head = st.number_input("Font titolo", min_value=30., max_value=99., format="%.1f", step=1.)
        with col_ftable: 
            fontsize_table = st.number_input("Font tabella", min_value=6., value=12., max_value=14., format="%.1f", step=0.5)

        page_layout_part_general()
        header_text(title, fontsize_head, com)

        df_race = df_race.reset_index(drop=True)
        df_race.index += 1

        table_class_time(df_race, fontsize=fontsize_table)

        if decision:
            st.markdown(f"<br><br><br>", unsafe_allow_html=True)
            textsplit = decision.splitlines()
            for x in textsplit:
                st.markdown(f"<div style='text-align: left;'><b>{x}</b></div>", unsafe_allow_html=True)



    elif kind == "time":
        df_race = df_race[cols_part_essential]

        glob_do_stage  = 'do_stage_'+event.replace(" ", "")+cat
        glob_do_class  = 'do_class_'+event.replace(" ", "")+cat

        label_stage = name_finals if st.session_state.get(glob_do_stage, True) else name_qualif
        label_class = (name_class if st.session_state.get(glob_do_class, False) and st.session_state.get(glob_do_stage, True)
                        else name_results if st.session_state.get(glob_do_class, False)
                        else name_startlist)
        
        col_com, col_giri = st.sidebar.columns(2)
        with col_com:
            do_stage = st.toggle(label_stage, value=st.session_state.get(glob_do_stage, True), key=glob_do_stage)
        with col_giri:
            do_class = st.toggle(label_class,value=st.session_state.get(glob_do_class, False), key=glob_do_class)

        df_race_all = pursuit_race(df_race, event, cat, do_stage, do_class)


        title = f"{label_class} - {event} {cat} - {label_stage} ({n_laps} giri)"
        decisione_txt = "Il secondo atleta parte sul rettilineo opposto."
        decisione_txt += "\nSi qualificano per le finali i migliori 4 tempi." if not do_stage else ""  

        title, decision = get_title_decision(label_class, event, cat, n_laps, title=title, decision=decisione_txt)

        col_fhead, col_ftable = st.sidebar.columns(2)
        with col_fhead:
            fontsize_head = st.number_input("Font titolo", min_value=30., max_value=99., format="%.1f", step=1.)
        with col_ftable: 
            fontsize_table = st.number_input("Font tabella", min_value=6., value=12., max_value=14., format="%.1f", step=0.5)


        page_layout_part_general()
        header_text(title, fontsize_head, com)

        if not do_class:

            table_part_ins(*df_race_all, fontsize=fontsize_table)
            df_race = df_race_all[0]
        


        # df_race = df_race.reset_index(drop=True)
        # df_race.index += 1

        # table_class_group(df_race, fontsize=fontsize_table)

        if decision:
            st.markdown(f"<br><br><br>", unsafe_allow_html=True)
            textsplit = decision.splitlines()
            for x in textsplit:
                st.markdown(f"<p style='text-align: left'><b>{x}</b></p>", unsafe_allow_html=True)









    # table_part_general(df_part_disc, fontsize=fontsize_table)










# Using object notation
# add_selectbox = st.sidebar.selectbox(
#     "How would you like to be contacted?",
#     ("Email", "Home phone", "Mobile phone")
# )

# # Using "with" notation
# with st.sidebar:
#     add_radio = st.radio(
#         "Choose a shipping method",
#         ("Standard (5-15 days)", "Express (2-5 days)")
#     )


# print_top_padding = st.sidebar.number_input("Insert a number")







# # df.style.hide_columns([hide_cols_list])

# import base64

# # Read the SVG file
# with open("/home/nic/al/commissaire/track/header/logo.svg", "rb") as image_file:
#     encoded_string = base64.b64encode(image_file.read()).decode()










# st.image('header/logo.svg')


# st.table(df)

# st.markdown(
#     """
#     <style>
#     .small-font {
#         font-size: 12px !important;
#     }
#     .extended-table {
#         width: 100% !important;
#         display: block;
#         overflow-x: auto;
#     }
#     </style>
#     """,
#     unsafe_allow_html=True
# )
# st.markdown('<div class="extended-table"><div class="small-font">', unsafe_allow_html=True)




# st.dataframe(df_part_s)
# st.markdown('</div></div>', unsafe_allow_html=True)

# edited_df = st.data_editor(df)