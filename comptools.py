import numpy as np
import pandas as pd
from pandas import DataFrame

#### Función Half-up value round. Se hace porque para python round(0.035) = round(0.045) = 0.4
# y esto claramente es incorrecto según lo que se nos enseña en la escuela
def HUP_round(series, decimals=3): # por ahora solo tolera rendondeo de decimales, no de ceros.
    factor = 10**decimals
    return np.floor(series * factor +0.5)/factor
####

#### Función para unir dos dataframes a partir de su columna de tiempo. Únicamente se hace la operación
# para las columnas
def time_join(
    dframe1: DataFrame,
    dframe2: DataFrame,
    df1_column: str | list[str],
    df2_column: str | list[str],
    decimals: int = 3,
    time_column1: int = 0,
    time_column2: int = 0
) -> DataFrame:
    
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
def RMSE(
    dframe1: DataFrame,
    dframe2: DataFrame,
    df1_column: str,
    df2_column: str,
    decimals: int = 3,
    time_column1: int = 0,
    time_column2 :int = 0
    ) -> float:
    
    if type(df1_column) != str or type(df2_column) != str:
        print('Error. Solo es posible obtener el error de dos columnas a la vez')
        return np.nan
    else:
        joined_result = time_join(dframe1, dframe2, df1_column, df2_column, decimals, time_column1, time_column2)

        if isinstance(joined_result, pd.DataFrame):
            joined_result['sqr. error'] = (joined_result[df1_column] - joined_result[df2_column])**2
            return np.sqrt(sum(joined_result['sqr. error']/joined_result.shape[0]))
        else:
            return np.nan

####

#### Función para calcular la derivada de una señal mediante diferenciación finita por método central. Solo soporta pasos más pequeños que 1
def derivative(
    dframe: DataFrame,
    column: str,
    normalize: int = 1,
    time_step: float = 0.001,
    time_column: int = 0
) -> DataFrame:
    decimals = len(str(time_step).split('.')[-1])
    df_columns = dframe.columns
    
    if column in df_columns:
        # col_index = dframe.columns.get_loc(column)
        dframe.iloc[:, time_column] = HUP_round(dframe.iloc[:, time_column], decimals)

        dframe = dframe.drop_duplicates(subset=df_columns[time_column])
        dframe = dframe.reset_index(drop=True)
        
        if normalize != 1:
            title = "(" + column + ")' normalized"
        else:
            title = "(" + column + ")'"

        dframe[title] = np.gradient(dframe[column], time_step)/normalize
        return dframe, title
        
    else:
        print('Error: Una de las columnas indicadas no se encuentra en su respectivo DataFrame')
        return 'Error'
####

#### Función para deparar los transitorios de el estado estacionaro de una señal, de esta manera, es posible evaluar estas dos secciones
# por separado usando el RMSE
def transient_cut(
    dframe: DataFrame,
    dt_criteria: float,
    df1_column: str,
    df2_column: str | None = None,
    normalize: int = 1
    ) -> list[DataFrame, DataFrame, DataFrame]:
    df_columns = dframe.columns

    if df1_column in df_columns:
        result, title_dt_1  = derivative(dframe, df1_column, normalize=normalize)
        result, title_ddt_1 = derivative(result, title_dt_1)

        mask_dt1  = abs(result[title_dt_1]) > dt_criteria  # Máscara de la primera derivada de la señal 1
        mask_ddt1 = abs(result[title_ddt_1]) > dt_criteria # Máscara de la segunda derivada de la señal 1

        mask_trn_1 = mask_dt1 | mask_ddt1   # Máscara para los transitorios de la señal 1
        mask_sst_1 = ~mask_dt1 & ~mask_ddt1 # Máscara para los estacionarios de la señal 1

        # Esto podría parecer redundante pero no lo es, ya que mask_trn y mask_sst podrían estar solo en
        # función de la señal 1 o en función de la señal 1 y 2; dependiendo de si se indicó una segunda 
        # columna que se encuentre en el dataframe
        mask_trn = mask_trn_1
        mask_sst = mask_sst_1


        if df2_column and df2_column in df_columns:
            result, title_dt_2  = derivative(result, df2_column, normalize=normalize)
            result, title_ddt_2 = derivative(result, title_dt_2)

            mask_dt2  = abs(result[title_dt_2]) > dt_criteria  # Máscara de la primera derivada de la señal 2
            mask_ddt2 = abs(result[title_ddt_2]) > dt_criteria # Máscara de la segunda derivada de la señal 2

            mask_trn_2 = mask_dt2 | mask_ddt2   # Máscara para los transitorios de la señal 2
            mask_sst_2 = ~mask_dt2 & ~mask_ddt2 # Máscara para los estacionarios de la señal 2

            mask_trn = mask_trn_1 | mask_trn_2 # Combinar las máscaras de la señal 1 y 2
            mask_sst = mask_sst_1 & mask_sst_2 #
            
        elif df2_column and df2_column not in df_columns:
            print(f'Error: La columna {df2_column} no se encuentra en el DataFrame')
            return 'Error'
        
        trnFrame = result[mask_trn]
        sstFrame = result[mask_sst]
        
        return result, trnFrame, sstFrame

    else:
        print(f'Error: La columna {df1_column} no se encuentra en el DataFrame')
        return 'Error'
