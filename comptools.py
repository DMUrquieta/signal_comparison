import numpy as np
import pandas as pd
from typing import Tuple
from pandas import DataFrame
from pandas import Series
from pandas._typing import Suffixes

#### Función Half-up value round. Se hace porque para python round(0.035) = round(0.045) = 0.4
# y esto claramente es incorrecto según lo que se nos enseña en la escuela
def HUP_round(series: float | Series, decimals: int = 3): # por ahora solo tolera rendondeo de decimales, no de ceros.
    factor = 10**decimals
    return np.floor(series * factor + 0.6)/factor
####

#### Función para unir dos dataframes a partir de su columna de tiempo. Únicamente se hace la operación
# para las columnas
def time_join(
    dframe1: DataFrame,
    dframe2: DataFrame,
    column_1: str | list[str],
    column_2: str | list[str],
    decimals: int = 3,
    time_column1: int = 0,
    time_column2: int = 0,
    suffixes: Suffixes = ("_serie_1", "_serie_2")
    ) -> DataFrame:
    
    df1_columns = dframe1.columns
    df2_columns = dframe2.columns

    column_1 = [column_1] if type(column_1) == str else column_1 # Transformar a lista si 
    column_2 = [column_2] if type(column_2) == str else column_2 # se da un índice
    
    dslindexer = dframe1.columns.get_indexer(column_1) # Obtener los índices de las columnas 
    pssindexer = dframe2.columns.get_indexer(column_2) # ingresadas de los dataframes
    
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
            right_on=df2_columns[time_column2],
            suffixes=suffixes
        )

        # result = result.drop(columns=df2_columns[time_column2])
        return result
    
    else: 
        if -1 in dslindexer:
            nindex = [col for col in column_1 if col not in df1_columns]
            print(f'\nLas siguientes columnas no se encuentran en el DataFrame 1: \n{nindex}')

        if -1 in pssindexer:
            nindex = [col for col in column_2 if col not in df2_columns]
            print(f'\nLas siguientes columnas no se encuentran en el DataFrame 2: \n{nindex}')

        return 'Error'
####

#### Función para obtemer Root Mean Squared Error entre 2 señales
def RMSE(
    dframe1: DataFrame,
    dframe2: DataFrame | None = None,
    column_1: str = 'Columna 1',
    column_2: str = 'Columna 2',
    decimals: int = 3,
    time_column1: int = 0,
    time_column2 :int = 0
    ) -> float:
    
    if type(column_1) != str or type(column_2) != str:
        print('Error. Es necesario ingresar el nombre de una columna del dataframe')
        return np.nan
    else:
        if isinstance(dframe2, pd.DataFrame):
            joined_result = time_join(dframe1, dframe2, column_1, column_2, decimals, time_column1, time_column2)
            column_1 = joined_result.columns[1]
            column_2 = joined_result.columns[2]
        else:
            if column_1 in dframe1.columns and column_2 in dframe1.columns:
                joined_result = dframe1
            else:
                print('Error: Una de las columnas indicadas no se encuentra en el DataFrame')
                return np.nan

        if isinstance(joined_result, pd.DataFrame):
            sqr_error = (joined_result[column_1] - joined_result[column_2])**2
            return np.sqrt(sum(sqr_error/joined_result.shape[0]))
        else:
            return np.nan
####

#### Función para calcular la derivada de una señal mediante diferenciación finita por método central. Solo soporta pasos más pequeños que 1
def derivative(
    dframe: DataFrame,
    column: str,
    time_step: float,
    normalize: int = 1,
    time_column: int = 0
    ) -> Tuple[DataFrame, str]:
    decimals = len(str(time_step).split('.')[-1])
    df_columns = dframe.columns
    
    if column in df_columns:
        # col_index = dframe.columns.get_loc(column)
        dframe.iloc[:, time_column] = HUP_round(dframe.iloc[:, time_column], decimals)

        dframe = dframe.drop_duplicates(subset=df_columns[time_column])
        dframe = dframe.reset_index(drop=True)
        
        if normalize != 1:
            print(f'Advertencia: La señal {column} se ha normalizado con respecto a {normalize}')
        # title = "(" + column + ")'"
        title = column + "'"

        dframe[title] = np.gradient(dframe[column], time_step)/normalize
        return dframe, title
        
    else:
        print('Error: Una de las columnas indicadas no se encuentra en su respectivo DataFrame')
        return 'Error'
####

#### Función para separar los transitorios de los segmentos en estado estacionario de una señal, de esta manera
# es posible evaluar estas dos secciones por separado usando el RMSE
def transient_cut(
    dframe: DataFrame,
    column_1: str,
    time_step: float,
    dt_threshold: int | float,
    normalize: int,
    ddt_threshold: int | float | None = None,
    column_2: str | None = None
    ) -> Tuple[DataFrame, Series, Series]:

    if ddt_threshold  is None: ddt_threshold  = dt_threshold
    df_columns = dframe.columns

    if column_1 in df_columns:
        result, title_dt_1  = derivative(dframe, column_1, normalize=normalize, time_step=time_step)
        result, title_ddt_1 = derivative(result, title_dt_1, normalize=1, time_step=time_step)

        mask_dt1  = abs(result[title_dt_1]) > dt_threshold # Máscara de la primera derivada de la señal 1
        mask_ddt1 = abs(result[title_ddt_1]) > ddt_threshold # Máscara de la segunda derivada de la señal 1

        mask_trn_1 = mask_dt1 | mask_ddt1   # Máscara para los transitorios de la señal 1
        mask_sst_1 = ~mask_dt1 & ~mask_ddt1 # Máscara para los estacionarios de la señal 1

        # Esto podría parecer redundante pero no lo es, ya que mask_trn y mask_sst podrían estar solo en
        # función de la señal 1 o en función de la señal 1 y 2; dependiendo de si se indicó una segunda 
        # columna que se encuentre en el dataframe
        mask_trn = mask_trn_1
        mask_sst = mask_sst_1


        if column_2 and column_2 in df_columns:
            result, title_dt_2  = derivative(result, column_2, normalize=normalize)
            result, title_ddt_2 = derivative(result, title_dt_2, normalize=1, time_step=time_step)

            mask_dt2  = abs(result[title_dt_2]) > dt_threshold # Máscara de la primera derivada de la señal 2
            mask_ddt2 = abs(result[title_ddt_2]) > ddt_threshold # Máscara de la segunda derivada de la señal 2

            mask_trn_2 = mask_dt2 | mask_ddt2   # Máscara para los transitorios de la señal 2
            mask_sst_2 = ~mask_dt2 & ~mask_ddt2 # Máscara para los estacionarios de la señal 2

            # Por esta declaración, la línea de la que se habló más arriba no es redundante. Ya que, dependiendo de si
            # hay 1 o 2 dataframes, mask_trn y mask_sst podrían ser diferentes.
            mask_trn = mask_trn_1 | mask_trn_2 # Combinar las máscaras de la señal 1 y 2
            mask_sst = mask_sst_1 & mask_sst_2 #
            
        elif column_2 and column_2 not in df_columns:
            print(f'Error: La columna {column_2} no se encuentra en el DataFrame')
            return 'Error'
        
        # trnFrame = result[mask_trn]
        # sstFrame = result[mask_sst]
        
        # return result, trnFrame, sstFrame
        # Mejor no entregamos 3 dataframes, sino un dataframe completo y 2 máscaras que el usuario puede usar para separar el dataframe
        # en transitorios y estacionarios sin utilizar memoria extra. Esto puede ayudar a reducir la memoria requerida al usar esta función.
        return result, mask_trn, mask_sst 

    else:
        print(f'Error: La columna {column_1} no se encuentra en el DataFrame')
        return 'Error'


