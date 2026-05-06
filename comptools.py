import numpy as np
import pandas as pd

#### Función Half-up value round. Se hace porque para python round(0.035) = round(0.045) = 0.4
# y esto claramente es incorrecto según lo que se nos enseña en la escuela
def HUP_round(series, decimals=3): # por ahora solo tolera rendondeo de decimales, no de ceros.
    factor = 10**decimals
    return np.floor(series * factor +0.5)/factor
####

#### Función para unir dos dataframes a partir de su columna de tiempo. Únicamente se hace la operación
# para las columnas
def time_join(dframe1, dframe2, df1_column, df2_column, decimals=3, time_column1=0, time_column2=0):
    df1_columns = dframe1.columns
    df2_columns = dframe2.columns

    df1_column = [df1_column] if type(df1_column) == str else df1_column # Transformar a lista si 
    df2_column = [df2_column] if type(df2_column) == str else df2_column # se da un índice
    
    dslindexer = dframe1.columns.get_indexer(df1_column) # Obtener los índices de las columnas 
    pssindexer = dframe2.columns.get_indexer(df2_column) # ingresadas de los df
    
    if -1 not in dslindexer and -1 not in pssindexer:

        dslindexer = np.insert(dslindexer, 0, time_column1) # Agregar las columnas de tiempo al indexador
        pssindexer = np.insert(pssindexer, 0, time_column2) # 

        dframe1 = dframe1.iloc[:, dslindexer] # Selección de las columnas indicadas por los
        dframe2 = dframe2.iloc[:, pssindexer] # indexadores

        dframe1.iloc[:,0] = HUP_round(dframe1.iloc[:,0], decimals) # Redondeo de las columnas de
        dframe2.iloc[:,0] = HUP_round(dframe2.iloc[:,0], decimals) # tiempo 

        dframe1 = dframe1.drop_duplicates(df1_columns[time_column1], keep='first', ignore_index=True)
        dframe2 = dframe2.drop_duplicates(df2_columns[time_column2], keep='first', ignore_index=True)

        result = pd.merge(
            dframe1, dframe2,
            how='inner',
            left_on=df1_columns[time_column1],
            right_on=df2_columns[time_column2]
        )

        result = result.drop(columns=df2_columns[time_column2])
        return result
    
    else: 
        if -1 in dslindexer:
            nindex = [col for col in df1_column if col not in df1_columns]
            print(f'\nLas siguientes columnas no se encuentran en el DataFrame 1: \n{nindex}')

        if -1 in pssindexer:
            nindex = [col for col in df2_column if col not in df2_columns]
            print(f'\nLas siguientes columnas no se encuentran en el DataFrame 2: \n{nindex}')

        return 'Error'
####

#### Función para obtemer Root Mean Squared Error entre 2 señales
def RMSE(dframe1, dframe2, df1_column, df2_column, decimals=3, time_column1=0, time_column2=0):
    df1_columns = dframe1.columns
    df2_columns = dframe2.columns
    
    if df1_column in df1_columns and df2_column in df2_columns:
        dslindex = dframe1.columns.get_loc(df1_column)
        pssindex = dframe2.columns.get_loc(df2_column)

        dframe1 = dframe1.iloc[:,[time_column1, dslindex]]
        dframe2 = dframe2.iloc[:,[time_column2, pssindex]]

        dframe1.iloc[:,0] = HUP_round(dframe1.iloc[:,0], decimals)
        dframe2.iloc[:,0] = HUP_round(dframe2.iloc[:,0], decimals)

        dframe1 = dframe1.drop_duplicates(df1_columns[time_column1], keep='first', ignore_index=True)
        dframe2 = dframe2.drop_duplicates(df2_columns[time_column2], keep='first', ignore_index=True)

        result = pd.merge(
            dframe1, dframe2,
            how='inner',
            left_on=df1_columns[time_column1],
            right_on=df2_columns[time_column2]
        )

        transient = result[result[df1_column]>0.02]

        result['sqr. error'] = (result[df1_column] - result[df2_column])**2
        return np.sqrt(sum(result['sqr. error']/result.shape[0]))

    else:
        if df1_column not in df1_columns:
            print(f'Error: La columna {df1_column} no se encuentra en su respectivo DataFrame')
        if df2_column not in df2_columns:
            print(f'Error: La columna {df2_column} no se encuentra en su respectivo DataFrame')
        return np.nan
####

#### Función para calcular la derivada de una señal mediante diferenciación finita por método central. Solo soporta pasos más pequeños que 1
def derivative(dframe, column, time_step=0.001, normalize=1, time_column=0):
    decimals = len(str(time_step).split('.')[-1])
    df_columns = dframe.columns
    
    if column in df_columns:
        # col_index = dframe.columns.get_loc(column)
        dframe.iloc[:, time_column] = HUP_round(dframe.iloc[:, time_column], decimals)

        dframe = dframe.drop_duplicates(subset=df_columns[time_column])
        dframe = dframe.reset_index(drop=True)
        
        if normalize != 1:
            title = 'd/dt ' + '(' + column + ') normalized'
        else:
            title = 'd/dt ' + '(' + column + ')'

        dframe[title] = np.gradient(dframe[column], time_step)/normalize
        return dframe, title
        
    else:
        print('Error: Una de las columnas indicadas no se encuentra en su respectivo DataFrame')
        return 'Error'
####