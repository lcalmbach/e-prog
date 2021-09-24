import streamlit as st
import json
import pandas as pd
import altair as alt
from st_aggrid import AgGrid

settings = {}
em_fact_ng = 196
em_fact_oil = 265

def get_data():
    # read file
    df = pd.read_csv('data.csv')
    return df

def get_ausgangslage(df):
    rec = df.iloc[0].to_dict()
    jahre = len(settings['model_years'])
    reduktion_pct_oel = 100-settings['oel_dez_pzt']
    reduktion_pct_gas = 100-settings['erdgas_dez_pzt']
    unit = '%' if (settings['show_abs_pct'].lower() == 'prozente') else 'GWh'
    text = f"""Im Jahr {settings['base_year']} beträgt der Heizölverbrauch von dezentralen Heizungen {rec['dez_oel']}GWh und soll ins Jahr {settings['target_year']} um {100-settings['oel_dez_pzt'] :.0f}% reduziert werden. 
    Der Verbrauch von dezentralen Erdgasheizungen beträgt {rec['dez_gas']}GWh und soll um {100-settings['erdgas_dez_pzt']}% reduziert werden. {reduktion_pct_gas / 100 * rec['dez_gas'] + reduktion_pct_oel / 100 * rec['dez_oel']}GWh fossile Energie 
    soll über {jahre} Jahre 1:1 durch Fernwärme ersetzt werden. Es müssen somit jährlich inkrementell {reduktion_pct_gas / 100 * rec['dez_gas'] / jahre :.1f} GWh Erdgas und {reduktion_pct_oel / 100 * rec['dez_oel']/jahre :.1f} GWh Heizöl kompensiert 
werden. Im definierten Szenario beträgt der Energiemix für die aufgestockte Fernwärme: {settings['erdgas'] :.1f}{unit} Erdgas, {settings['abfall'] :.1f}{unit} Kehricht/Schlamm, {settings['geotherm'] :.1f}{unit} Umweltwärme 
und {settings['holz'] :.1f}{unit} Holz. Es werden folgende CO2-Emissionsfaktoren verwendet: Erdgas: {em_fact_ng}g/kWh, Heizöl: {em_fact_oil}g/kWh. Holz, Umweltwärme und Kehricht werden als 100% erneuerbar betrachtet.
    """        
    return text

def get_total_subst(df):
    init_rec = df.iloc[0].to_dict()
    result = init_rec['dez_gas'] * (1-settings['erdgas_dez_pzt'] / 100) + init_rec['dez_oel'] * (1-settings['oel_dez_pzt'] / 100)
    return int(result)


def  calc_model(df):
    init_rec = df.iloc[0].to_dict()

    total_substitute_energy = init_rec['dez_gas'] * (settings['erdgas_dez_pzt'] / 100) + init_rec['dez_oel'] * (settings['oel_dez_pzt'] / 100)
    
    # st.write(total_substitute_energy, settings['model_years'], total_substitute_energy / len( settings['model_years']))
    ng_reduction = init_rec['dez_gas'] / len( settings['model_years']) * (1 - settings['erdgas_dez_pzt'] / 100) 
    oil_reduction = init_rec['dez_oel'] / len( settings['model_years'])  * (1 - settings['oel_dez_pzt'] / 100)
    total_substitute_energy = ng_reduction + oil_reduction
    
    if settings['show_abs_pct'].lower() == 'prozente':
        ng_subst = total_substitute_energy * settings['erdgas'] / 100
        abfall_subst = total_substitute_energy * settings['abfall'] / 100
        holz_subst = total_substitute_energy * settings['holz'] / 100
        geotherm_subst = total_substitute_energy * settings['geotherm'] / 100
    else:
        ng_subst = settings['erdgas']
        abfall_subst = settings['abfall']
        holz_subst = settings['holz'] 
        geotherm_subst = settings['geotherm'] 

    i = 1
    for year in  settings['model_years']:
        _temp = init_rec.copy()
        _temp['dez_oel'] = init_rec['dez_oel'] - (i * oil_reduction)
        _temp['dez_gas'] = init_rec['dez_gas'] - (i * ng_reduction)
        _temp['fw_heisswasser'] = init_rec['fw_heisswasser'] + (i * ng_reduction)
        _temp['fw_holz'] = init_rec['fw_holz'] + (i * holz_subst)
        _temp['fw_geotherm'] = init_rec['fw_geotherm'] + (i * geotherm_subst)
        _temp['fw_erdgas'] = init_rec['fw_erdgas'] + (i * ng_subst)
        _temp['fw_abfall'] = init_rec['fw_abfall'] + (i * abfall_subst)

        _temp['jahr'] = year 
        df = df.append(_temp, ignore_index=True)
        i+=1

    return df


def plot_bar(df, title, x):
    chart = alt.Chart(df).mark_bar(width = 20).encode(
        x=alt.X('jahr', axis=alt.Axis(format='N', title = ''), scale=alt.Scale(domain=[2018,settings['target_year']])),
        y=alt.Y(f'{x}:Q', stack='zero'),
        color='Energieträger:N',
        tooltip = list(df.columns)
    ).properties(width = 1000, title = title)
    st.altair_chart(chart)
    with st.expander('Tabelle', expanded= False):
        AgGrid(df,key=title)
    st.markdown('---')

def get_plot_df(df):
    lst_plot_df = []

    _temp = df.melt(id_vars=['jahr'], 
        value_vars=['dez_oel','dez_gas','fw_holz','fw_geotherm','fw_erdgas','fw_abfall'], var_name='Energieträger', 
        value_name='Verbrauch (GWh)')
    lst_plot_df.append(_temp) 

    df['co2_oel'] = df['dez_oel'] * em_fact_oil
    df['co2_gas'] = df['dez_gas'] * em_fact_ng
    df['co2_fw_gas'] = df['fw_erdgas'] * em_fact_ng
    _temp = df.melt(id_vars=['jahr'], 
        value_vars=['co2_oel','co2_gas','co2_fw_gas'], var_name='Energieträger', 
        value_name='CO2 (t)')
    lst_plot_df.append(_temp) 

    df['co2_oel'] = df['dez_oel'] * 256
    df['co2_gas'] = df['dez_gas'] * 196 +  df['fw_erdgas'] * 196
    _temp = df.melt(id_vars=['jahr'], 
        value_vars=['co2_oel','co2_gas'], var_name='Energieträger', 
        value_name='CO2 (t)')
    lst_plot_df.append(_temp) 

    return lst_plot_df


def main():


    st.set_page_config(
            page_title="e-sim",
            page_icon="🔥",
            layout="wide",
            initial_sidebar_state="expanded",
        )

    st.sidebar.markdown(f"## 🔥 Ersatz Erdgas/Öl Heizungen")
    initial_df = get_data()
    
    settings['target_year'] = st.sidebar.number_input('Ablösung bis',2030, 2100)
    settings['base_year'] = initial_df['jahr'].min()
    settings['first_year'] = settings['base_year'] + 1
    settings['model_years'] = range(settings['first_year'], settings['target_year'] + 1)
    
    st.sidebar.write(f"Reduktion fossile dezentrale Heizungen bis {settings['target_year']} auf:")
    settings['erdgas_dez_pzt'] = st.sidebar.slider(f"Anteil Erdgas im Jahr {settings['target_year']}", 0,100, 0)
    settings['oel_dez_pzt'] = st.sidebar.slider(f"Anteil Heizöl im Jahr {settings['target_year']}",0, 100, 0)
    
    st.sidebar.write('Zusammensetzung Input Fernwärme substituiert')
    settings['show_abs_pct'] = st.sidebar.radio("Anzeige", ['absolut (GWh)','Prozente'])
    if settings['show_abs_pct'].lower() == 'prozente':
        settings['holz'] = st.sidebar.slider("Anteil Holz (%)", 0,100,50)
        settings['abfall'] = st.sidebar.slider("Anteil Kehricht (%)",0, 100 - settings['holz'], 25)
        settings['geotherm'] = st.sidebar.slider("Anteil Erdwärme (%)", 0, 100 - settings['holz']  - settings['abfall'] , 0)
        settings['erdgas'] = 100 - settings['holz'] - settings['abfall'] - settings['geotherm']
        st.sidebar.write("Anteil Erdgas")
        st.sidebar.write(settings['erdgas'])
    else:
        subst_total = get_total_subst(initial_df) / len(settings['model_years'])
        
        settings['holz'] = st.sidebar.slider("Zunahme Holz GWh/Jahr", 0.0, subst_total, float(subst_total))
        if  subst_total - settings['holz'] > 0.1:
            settings['abfall'] = st.sidebar.slider("Zunahme Kehricht GWh/Jahr",0.0, subst_total - settings['holz'], 0.0)
        else:
            settings['abfall'] = 0
        if (subst_total - settings['holz'] - settings['abfall']) > 0.1:
            settings['geotherm'] = st.sidebar.slider("Zunahme Erdwärme GWh/Jahr", 0.0, subst_total - settings['holz'] - settings['abfall'] , 0.0)
        else:
            settings['geotherm'] = 0
        if subst_total - settings['holz'] - settings['abfall'] - settings['geotherm'] > 0.1:
            settings['erdgas'] = subst_total - settings['holz'] - settings['abfall'] - settings['geotherm']
            st.sidebar.write(f"Zunahme Erdgas GWh/Jahr: {settings['erdgas'] :.1f}")
        else:
            settings['erdgas'] = 0
            

    st.write("**Ausgangslage**")
    st.markdown(get_ausgangslage(initial_df))
    st.write("**Prognose**")
    df = calc_model(initial_df)
    lst_df_plot = get_plot_df(df)
    plot_bar(lst_df_plot[0], 'Verbrauch nach Energieträger und Quelle','Verbrauch (GWh)')
    plot_bar(lst_df_plot[1], 'CO2 Produktion nach Energieträger und Quelle', 'CO2 (t)')
    plot_bar(lst_df_plot[2], 'CO2 Produktion nach Energieträger', 'CO2 (t)')

if __name__ == '__main__':
    main()
