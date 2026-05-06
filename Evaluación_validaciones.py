##### Introducción #################################################################################################
## Importar librerías
import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
os.environ["PATH"] = r"C:\Program Files\DIgSILENT\PowerFactory 2025 SP1" + os.environ["PATH"]  # Importamos estas librerías y archivos para enlazar nuestro intérprete de python (En mi caso, Spyder) con DIgSILENT
sys.path.append("C:\\Program Files\\DIgSILENT\\PowerFactory 2025 SP1\\Python\\3.11")
import powerfactory

### Dirección para guardar los resultados de DIgSILENT
dsl_folder_main = r"C:\Users\diego.montesanos\OneDrive - Funken Ingenieros S.A. de C.V\Documentos\FKTrabajo\2026 22 Dinámica PSSE Vs DIgSILENT\REPC_D"

#### Valores nominales
# Datos del POI
VnPOI = 115 #kV

# Datos del inversor
Sn = 120 # MW
Vterm = 0.6 #kV
IBaseIBR = Sn/(np.sqrt(3)*Vterm) # kA

#### Modos de control
REPC_D_modes = [
    'REPC_D Modo 01', # Reactiva
    'REPC_D Modo 02', # Reactiva con PI de P
    'REPC_D Modo 03', # Voltaje
    'REPC_D Modo 04', # Voltaje con PI de P
    'REPC_D Modo 05', # Factor de potencia
    'REPC_D Modo 06'  # Factor de potencia con PI de P
]

REEC_E_modes = [
    'REEC_E Modo 01',
    'REEC_E Modo 03',
    'REEC_E Modo 05',
    'REEC_E Modo 06'
]

#### Pruebas a realizar
dsl_names = {
    0 : ['00 - Inicio Plano.csv', "ARRANQUE_PLANO\ibr_plano.csv"],
    1 : ['01 - Falla parcial.csv', "FALLAS\FALLA_PARCIAL\ibr_falla_parcial.csv"],
    2 : ['02 - Falla total.csv', "FALLAS\FALLA_TOTAL\ibr_falla_total.csv"],
    3 : ['03 - Perturbación de fase.csv', "PERTURBACIONES\PERT_FASE\ibr_pert_fase.csv"],
    4 : ['04 - Perturbación de frecuencia.csv', "PERTURBACIONES\PERT_FRECUENCIA - PASO\ibr_pert_frq.csv"],
    5 : ['05 - Perturbación de voltaje.csv', "PERTURBACIONES\PERT_VOLTAJE\ibr_pert_voltaje.csv"],
    6 : ['06 - Escalón Paux.csv', "ESCALONES\ESC_PAUX_REECE\ibr_escalones_paux.csv"],
    7 : ['07 - Escalón Pref.csv', "ESCALONES\ESC_PREF_REECE\ibr_escalones_pref.csv"],
    8 : ['08 - Escalón Qref.csv', "ESCALONES\ESC_QREF_REECE\ibr_escalones_qref.csv"],
    9 : ['09 - REPCD Escalón Qref.csv', "ESCALONES\ESC_QREF_PLNTB\ibr_escalones_qref.csv"],
    10: ['10 - REPCD Escalón Vref.csv', "ESCALONES\ESC_VREF_PLNTB\ibr_escalones_vref.csv"],
    11: ['11 - REPCD Escalón PFref.csv', "ESCALONES\ESC_PFREF_PLNTB\ibr_escalones_pfref.csv"],
    12: ['12 - REPCD Escalón Paux.csv', "ESCALONES\ESC_PREF_PLNTB\ibr_escalones_pref.csv"],
    13: ['13 - REPCD Escalón Fref.csv', "ESCALONES\ESC_FREF_PLNTB\ibr_escalones_fref.csv"]
}

#### Conectar con DigSILENT
app = powerfactory.GetApplicationExt()
# app.Show()
user = app.GetCurrentUser()
oProject = user.GetContents('DYN DIgSILENT x PSSE.IntPrj')[0]
oProject.Activate()
####################################################################################################################

##### Definición de funciones ######################################################################################
#### Función para calcular las columnas adicionales en el DataFrame de PSS/E
def read_csv_pss_file(path, test_name):
    directory = path + test_name
    if directory is None or not os.path.isfile(directory):
        app.PrintWarn(f"Prueba '{test_name}' de PSS/E no disponible.")
        return 'Error'
    else:
        pssframe = pd.read_csv(directory, skiprows=1)
        Vt_angle = pssframe[' IBRT_ANGLE']
        
        pssframe['IBR_P (MW)']    = pssframe[' IBR_P']*100
        pssframe['IBR_Q (MVAR)']  = pssframe[' IBR_Q']*100
        pssframe['IBR_S (MVA)']   = np.sqrt(pssframe['IBR_P (MW)']**2 + pssframe['IBR_Q (MVAR)']**2)

        pssframe['IBR_V (kV)']    = pssframe[' IBRT_V']*Vterm
        pssframe['IBR_VINT (kV)'] = pssframe[' IBR_VT']*Vterm
        
        pssframe['IBR_ID (kA)']   = pssframe['IBR_P (MW)']/np.sqrt(3)/pssframe['IBR_VINT (kV)']
        pssframe['IBR_IQ (kA)']   = pssframe['IBR_Q (MVAR)']/np.sqrt(3)/pssframe['IBR_VINT (kV)']
        pssframe['IBR_pf (pu)']   = abs(pssframe['IBR_P (MW)']/pssframe['IBR_S (MVA)'])

        pssframe['PLL_DELTA (Degree)'] = pssframe[' IBR_DELTA_PLL']*180/np.pi
        pssframe['VQ_PLL (kV)']   = pssframe['IBR_V (kV)']*np.sin((Vt_angle-pssframe['PLL_DELTA (Degree)'])*np.pi/180)

        pssframe['POI_V (kV)']    = pssframe[' POI_V']*VnPOI
        pssframe['POI_S (MVA)']   = np.sqrt(pssframe[' POI_P']**2 + pssframe[' POI_Q']**2)
        pssframe['POI_pf (pu)']   = abs(pssframe[' POI_P']/pssframe['POI_S (MVA)'])
        pssframe['POI_FRQ (Hz)']  = pssframe[' POI_FREQ']*60+60
        return pssframe
####

#### Función para procesar los encabezados del archivo de resultados de DIgSILENT
def read_csv_dsl_file(path , test_dict, test_key):
    test_name = test_dict.get(test_key, 'Error')[0]
    directory = path + "\\" + test_name
    if directory is None or not os.path.isfile(directory):
        app.PrintWarn(f"Prueba {test_key:02d} de DIgSILENT no disponible.")
        return 'Error'
    else:
        dslframe = pd.read_csv(directory, header=None, low_memory=False)
        tmprow = dslframe.iloc[0].astype(str) + ' ' + dslframe.iloc[1].astype(str)
        tmp_df = dslframe.drop([0,1], axis=0)
        dslframe = pd.concat([tmprow.to_frame().T, tmp_df], ignore_index=True)
        dslframe.iloc[0,0] = 'Time in S'
        dslframe.columns = dslframe.iloc[0]
        dslframe.drop([0], axis=0, inplace=True)
        dslframe = dslframe.apply(pd.to_numeric)

        dslframe['POI m:cosphi:bus1'] = dslframe['POI m:cosphi:bus1'].abs()

        return dslframe
####
    
#### Función Half-up value round. Se hace porque para python round(0.035) = round(0.045) = 0.4
# y esto claramente es incorrecto según lo que se nos enseña en la escuela
def HUP_round(series, decimals):
    factor = 10**decimals
    return np.floor(series * factor +0.5)/factor
####

#### Función para obtemer Root Mean Squared Error entre 2 señales
def RMSE(dslframe, pssframe, dslcolumn, psscolumn):
    dsl_columns = dslframe.columns
    pss_columns = pssframe.columns
    
    if dslcolumn in dsl_columns and psscolumn in pss_columns:
        dslindex = dslframe.columns.get_loc(dslcolumn)
        pssindex = pssframe.columns.get_loc(psscolumn)

        dslframe = dslframe.iloc[:,[0, dslindex]]
        pssframe = pssframe.iloc[:,[0, pssindex]]

        dslframe.iloc[:,0] = HUP_round(dslframe.iloc[:,0], 3)
        pssframe.iloc[:,0] = HUP_round(pssframe.iloc[:,0], 3)

        result = pd.merge(
            dslframe, pssframe,
            how='inner',
            left_on=dsl_columns[0],
            right_on=pss_columns[0]
        )
        result = result.drop(columns=pss_columns[0])
        result['sqr. error'] = (result[dslcolumn] - result[psscolumn])**2
        return np.sqrt(sum(result['sqr. error']/result.shape[0]))

    else:
        app.PrintError('Una de las columnas indicadas no se encuentra en su respectivo DataFrame')
        return 'Error'
####
    
#### Función para calcular la derivada de una señal mediante diferenciación finita por método central
def derivative(dframe, column, time_step):
    df_columns = dframe.columns
    
    if column in df_columns:
        col_index = dframe.columns.get_loc(column)
        dframe.iloc[:,0] = HUP_round(dframe.iloc[:,0], 3)

        dframe = dframe.drop_duplicates(subset=df_columns[0])
        dframe = dframe.reset_index(drop=True)
        
        title = 'd/dt ' + '(' + column + ')'

        dframe[title] = np.gradient(dframe[column], time_step)
        return dframe, title
        
    else:
        app.PrintError('Una de las columnas indicadas no se encuentra en su respectivo DataFrame')
        return 'Error'
####
####################################################################################################################

##### Pruebas con el Control de planta, control eléctrico y convertidor ############################################
oFoldVarts = app.GetProjectFolder('scheme')     # Seleccionamos el folder de Variaciones
oFoldStudyGral = app.GetProjectFolder('study')  # Seleccionamos el folder de Casos de estudio
oFoldREECE = oFoldVarts.GetContents('REEC_E')[0]
oFoldREPCD = oFoldVarts.GetContents('REPC_D')[0]

app.EchoOff()
app.ClearOutputWindow()

#### Iteración de cada prueba dinámica en cada modo de configuración de los controles
## Iteración de los modos del control de planta

errors = {
    'REPC_D mode': [],
    'REEC_E mode': [],
    'Prueba': [],
    'POI V': [],
    'POI FRQ': [],
    'POI Q': [],
    'POI P': [],
    'POI PF': [],
    'POI Angle': [],
    'IBT Vt': [],
    'IBR Vq': [],
    'IBR ID': [],
    'IBR IQ': [],
    'IBR P': [],
    'IBR Q': [],
    'IBR PF': [],
    'IBR Angle': []
    }

app.PrintPlain('Realizando simulaciones dinámicas...\n')
print("Realizando simulaciones dinámicas...\n")
for REPC_D_mode in REPC_D_modes:
    oVarsREPCD = oFoldREPCD.GetContents(REPC_D_mode)[0]  # Obtenemos la Variacion del REPC_D que queremos activar para cada Caso de estudio
    oStgeREPCD = oVarsREPCD.GetContents('*.IntSstage')[0]

    ## Iteración de los modos del control eléctrico
    for REEC_E_mode in REEC_E_modes:
        sFold = REPC_D_mode + " - REEC_E " + REEC_E_mode[-2:]

        oFoldStudy = oFoldStudyGral.GetContents(sFold)[0]    # Seleccionar el folder correspondiente al modo de configuración de los controles
        app.PrintPlain(f"Procesando el folder: {oFoldStudy}")
        print(f"Procesando el folder: {oFoldStudy.loc_name}")
        oVarsREECE = oFoldREECE.GetContents(REEC_E_mode)[0]  # Obtenemos la Variacion que queremos activar para cada caso de estudio
        
        dsl_folder = dsl_folder_main + "\\" + sFold
        os.makedirs(dsl_folder, exist_ok=True)

        # Todos los casos de estudio en el folder especificado
        sStudyCase = oFoldStudy.GetContents('*.IntCase')
        sStudyCase.sort(key=lambda x: x.loc_name)  # Ordenamos los casos de estudio por nombre para que se guarden en el mismo orden que los archivos de resultados

        ## Iteración de las pruebas dinámicas
        for oStudyCase in sStudyCase:
            nCase = int(oStudyCase.loc_name[0:2])
            if nCase in dsl_names.keys():
                app.PrintPlain(f"   Procesando el caso de estudio: {oStudyCase}...")
                print(f"   Procesando el caso de estudio: {oStudyCase.loc_name}...")
                
                # oStudyCase.Activate()

                # sActiveVar = app.GetActiveNetworkVariations()   # Obtenemos las variaciones activas en el caso de estudio
                # [oActiveVar.Deactivate() for oActiveVar in sActiveVar]
                # oVarsREECE.Activate()
                # oVarsREPCD.Activate()
                # oStgeREPCD.Activate(1)
                
                # oInit = oStudyCase.GetContents('*.ComInc')[0]
                # oRun  = oStudyCase.GetContents('*.ComSim')[0]
                # oInit.Execute()
                # oRun.Execute()

                # oElmRes = app.GetFromStudyCase('ElmRes')
                # oElmExp = app.GetFromStudyCase('ComRes')

                # oElmExp.iopt_exp = 6
                # oElmExp.f_name = dsl_folder + "\\" + dsl_names[nCase][0]
                # oElmExp.pResult = oElmRes
                # oElmExp.Execute()


                ## Leer los resultados de las pruebas de DIgSILENT
                # app.PrintPlain(f"\n     Leyendo los resultados de las pruebas de DIgSILENT...")
                dsl_data = read_csv_dsl_file(dsl_folder, dsl_names, nCase)

        
                #  Método para leer archivos de PSS/E (Es específicp de este proyecto y no puede generalizarse. Sin embargo, puede servir para ser usado como referencia)
                dir_temp = r'X:\2026 Modelos IBR PSSE - DIgSILENT\REGCC + REECE + PLNTB - PSSE'
                dir_repc = "\\" + REPC_D_mode[7:].upper()
                dir_reec = " - " + 'REECE ' + REEC_E_mode[7:].upper() + "\\"
                pss_path = dir_temp + dir_repc + dir_reec
                pss_data = read_csv_pss_file(pss_path, dsl_names[nCase][1])

                if isinstance(pss_data, pd.DataFrame) and isinstance(dsl_data, pd.DataFrame):
                    errors['REPC_D mode'].append(REPC_D_mode)
                    errors['REEC_E mode'].append(REEC_E_mode)
                    errors['Prueba'].append(nCase)
                    errors['POI V'].append(RMSE(dsl_data, pss_data, 'POI Bus m:Ul in kV', 'POI_V (kV)')/VnPOI*100)
                    errors['POI FRQ'].append(RMSE(dsl_data, pss_data, 'POI n:fehz:bus1 in Hz', 'POI_FRQ (Hz)')/60*100)
                    errors['POI Q'].append(RMSE(dsl_data, pss_data, 'POI m:Qsum:bus1 in Mvar', ' POI_Q')/Sn*100)
                    errors['POI P'].append(RMSE(dsl_data, pss_data, 'POI m:Psum:bus1 in MW', ' POI_P')/Sn*100)
                    errors['POI PF'].append(RMSE(dsl_data, pss_data, 'POI m:cosphi:bus1', 'POI_pf (pu)')*100)
                    errors['POI Angle'].append(RMSE(dsl_data, pss_data, 'POI Bus m:phiu in deg', ' POI_ANGLE')/360*100)
                    errors['IBT Vt'].append(RMSE(dsl_data, pss_data, 'IBR n:Ul:bus1 in kV', 'IBR_V (kV)')/Vterm*100)
                    errors['IBR Vq'].append(RMSE(dsl_data, pss_data, 'REGC_C c:uq', 'VQ_PLL (kV)')/Vterm*100)
                    errors['IBR ID'].append(RMSE(dsl_data, pss_data, 'IBR m:I1P:bus1 in kA', 'IBR_ID (kA)')/IBaseIBR*100)
                    errors['IBR IQ'].append(RMSE(dsl_data, pss_data, 'IBR m:I1Q:bus1 in kA', 'IBR_IQ (kA)')/IBaseIBR*100)
                    errors['IBR Q'].append(RMSE(dsl_data, pss_data, 'IBR m:Qsum:bus1 in Mvar', 'IBR_Q (MVAR)')/Sn*100)
                    errors['IBR P'].append(RMSE(dsl_data, pss_data, 'IBR m:Psum:bus1 in MW', 'IBR_P (MW)')/Sn*100)
                    errors['IBR PF'].append(RMSE(dsl_data, pss_data, 'IBR m:cosphi:bus1', 'IBR_pf (pu)')*100)
                    errors['IBR Angle'].append(RMSE(dsl_data, pss_data, 'Terminal 5 m:phiurel in deg', 'PLL_DELTA (Degree)')/360*100)
                else:
                    print('   Caso de estudio no disponible')


app.EchoOn()

errors_df = pd.DataFrame(errors)
errors_df.to_csv(r'X:\2026 Modelos IBR PSSE - DIgSILENT\Reporte_RMSE.csv', index=False)
errors_df['Mode'] = 'PC' + errors_df['REPC_D mode'].str[-2:] + ' - EC' + errors_df['REEC_E mode'].str[-2:]


df_prueba_01 = errors_df[errors_df['Prueba'] == 1].sort_values('Mode')
df_prueba_02 = errors_df[errors_df['Prueba'] == 2].sort_values('Mode')
df_prueba_03 = errors_df[errors_df['Prueba'] == 3].sort_values('Mode')
df_prueba_04 = errors_df[errors_df['Prueba'] == 4].sort_values('Mode')
df_prueba_05 = errors_df[errors_df['Prueba'] == 5].sort_values('Mode')
df_prueba_06 = errors_df[errors_df['Prueba'] == 6].sort_values('Mode')
df_prueba_09 = errors_df[errors_df['Prueba'] == 9].sort_values('Mode')
df_prueba_10 = errors_df[errors_df['Prueba'] == 10].sort_values('Mode')
df_prueba_11 = errors_df[errors_df['Prueba'] == 11].sort_values('Mode')
df_prueba_12 = errors_df[errors_df['Prueba'] == 12].sort_values('Mode')
df_prueba_13 = errors_df[errors_df['Prueba'] == 13].sort_values('Mode')

fig, ax = plt.subplots(2,2, figsize=(15,10))
ax[0,0].plot(df_prueba_01['Mode'], df_prueba_01['POI V'], label='01 - Falla parcial')
ax[0,0].plot(df_prueba_02['Mode'], df_prueba_02['POI V'], label='02 - Falla total')
ax[0,0].plot(df_prueba_03['Mode'], df_prueba_03['POI V'], label='03 - Perturbación θ')
ax[0,0].plot(df_prueba_04['Mode'], df_prueba_04['POI V'], label='04 - Perturbación ω')
ax[0,0].plot(df_prueba_05['Mode'], df_prueba_05['POI V'], label='05 - Perturbación V')
ax[0,0].plot(df_prueba_06['Mode'], df_prueba_06['POI V'], label='06 - Escalón Paux')
ax[0,0].plot(df_prueba_09['Mode'], df_prueba_09['POI V'], label='09 - REPCD Escalón Qref')
ax[0,0].plot(df_prueba_10['Mode'], df_prueba_10['POI V'], label='10 - REPCD Escalón Vref')
ax[0,0].plot(df_prueba_11['Mode'], df_prueba_11['POI V'], label='11 - REPCD Escalón PFref')
ax[0,0].plot(df_prueba_12['Mode'], df_prueba_12['POI V'], label='12 - REPCD Escalón Paux')
ax[0,0].plot(df_prueba_13['Mode'], df_prueba_13['POI V'], label='13 - REPCD Escalón ωref')
ax[0,0].tick_params(axis='x', rotation=90)
ax[0,0].set_title('Voltaje en el POI')
ax[0,0].legend()
ax[0,0].grid()

ax[0,1].plot(df_prueba_01['Mode'], df_prueba_01['POI FRQ'], label='01 - Falla parcial')
ax[0,1].plot(df_prueba_02['Mode'], df_prueba_02['POI FRQ'], label='02 - Falla total')
ax[0,1].plot(df_prueba_03['Mode'], df_prueba_03['POI FRQ'], label='03 - Perturbación θ')
ax[0,1].plot(df_prueba_04['Mode'], df_prueba_04['POI FRQ'], label='04 - Perturbación ω')
ax[0,1].plot(df_prueba_05['Mode'], df_prueba_05['POI FRQ'], label='05 - Perturbación V')
ax[0,1].plot(df_prueba_06['Mode'], df_prueba_06['POI FRQ'], label='06 - Escalón Paux')
ax[0,1].plot(df_prueba_09['Mode'], df_prueba_09['POI FRQ'], label='09 - REPCD Escalón Qref')
ax[0,1].plot(df_prueba_10['Mode'], df_prueba_10['POI FRQ'], label='10 - REPCD Escalón Vref')
ax[0,1].plot(df_prueba_11['Mode'], df_prueba_11['POI FRQ'], label='11 - REPCD Escalón PFref')
ax[0,1].plot(df_prueba_12['Mode'], df_prueba_12['POI FRQ'], label='12 - REPCD Escalón Paux')
ax[0,1].plot(df_prueba_13['Mode'], df_prueba_13['POI FRQ'], label='13 - REPCD Escalón Fref')
ax[0,1].set_ylim(0, 0.02)
ax[0,1].tick_params(axis='x', rotation=90)
ax[0,1].set_title('Frecuencia en el POI')
ax[0,1].legend()
ax[0,1].grid()

ax[1,0].plot(df_prueba_01['Mode'], df_prueba_01['POI P'], label='01 - Falla parcial')
ax[1,0].plot(df_prueba_02['Mode'], df_prueba_02['POI P'], label='02 - Falla total')
ax[1,0].plot(df_prueba_03['Mode'], df_prueba_03['POI P'], label='03 - Perturbación θ')
ax[1,0].plot(df_prueba_04['Mode'], df_prueba_04['POI P'], label='04 - Perturbación ω')
ax[1,0].plot(df_prueba_05['Mode'], df_prueba_05['POI P'], label='05 - Perturbación V')
ax[1,0].plot(df_prueba_06['Mode'], df_prueba_06['POI P'], label='06 - Escalón Paux')
ax[1,0].plot(df_prueba_09['Mode'], df_prueba_09['POI P'], label='09 - REPCD Escalón Qref')
ax[1,0].plot(df_prueba_10['Mode'], df_prueba_10['POI P'], label='10 - REPCD Escalón Vref')
ax[1,0].plot(df_prueba_11['Mode'], df_prueba_11['POI P'], label='11 - REPCD Escalón PFref')
ax[1,0].plot(df_prueba_12['Mode'], df_prueba_12['POI P'], label='12 - REPCD Escalón Paux')
ax[1,0].plot(df_prueba_13['Mode'], df_prueba_13['POI P'], label='13 - REPCD Escalón Fref')
ax[1,0].set_ylim(0, 0.25)
ax[1,0].tick_params(axis='x', rotation=90)
ax[1,0].set_title('Potencia Activa en el POI ')
ax[1,0].legend()
ax[1,0].grid()

ax[1,1].plot(df_prueba_01['Mode'], df_prueba_01['POI Q'], label='01 - Falla parcial')
ax[1,1].plot(df_prueba_02['Mode'], df_prueba_02['POI Q'], label='02 - Falla total')
ax[1,1].plot(df_prueba_03['Mode'], df_prueba_03['POI Q'], label='03 - Perturbación θ')
ax[1,1].plot(df_prueba_04['Mode'], df_prueba_04['POI Q'], label='04 - Perturbación ω')
ax[1,1].plot(df_prueba_05['Mode'], df_prueba_05['POI Q'], label='05 - Perturbación V')
ax[1,1].plot(df_prueba_06['Mode'], df_prueba_06['POI Q'], label='06 - Escalón Paux')
ax[1,1].plot(df_prueba_09['Mode'], df_prueba_09['POI Q'], label='09 - REPCD Escalón Qref')
ax[1,1].plot(df_prueba_10['Mode'], df_prueba_10['POI Q'], label='10 - REPCD Escalón Vref')
ax[1,1].plot(df_prueba_11['Mode'], df_prueba_11['POI Q'], label='11 - REPCD Escalón PFref')
ax[1,1].plot(df_prueba_12['Mode'], df_prueba_12['POI Q'], label='12 - REPCD Escalón Paux')
ax[1,1].plot(df_prueba_13['Mode'], df_prueba_13['POI Q'], label='13 - REPCD Escalón Fref')
ax[1,1].set_ylim(0, 0.25)
ax[1,1].tick_params(axis='x', rotation=90)
ax[1,1].set_title('Potencia Reactiva en el POI')
ax[1,1].legend()
ax[1,1].grid()

fig.suptitle('Porcentaje de RMSE de señales en el POI para cada prueba')
fig.tight_layout()
plt.show()

print('Fin del programa')