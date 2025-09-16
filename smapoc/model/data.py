import pandas as pd
import numpy as np
import datetime as dt



class DataHandler:
    def __init__(self):
        self.data = pd.DataFrame(columns=['time', 'res1', 'res2', 'pow1', 'pow2', 'pow3'])
        self.data = self.data.astype({'time': 'datetime64[ns]',
                                      'res1': 'int',
                                      'res2': 'int',
                                      'pow1': 'int',
                                      'pow2': 'int',
                                      'pow3': 'int'})
        print(f'My Datatypes:\n{self.data.dtypes}')

    def add_line(self, mydict):
        data_in = mydict
        data_in['time'] = dt.datetime.now()
        dummy_df = pd.DataFrame(data_in, index=[0])
        self.data = pd.concat([self.data, dummy_df])

