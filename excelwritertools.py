### this is how to do styling:

ids_to_names = {'u-56-21617':'Samanta Cardona',
'c-169766':'Luis Velasquez',
'c-189101':'Jarrett English',
'foup6emzlsdum7':'Laura Pastrana'}

out_file = 'RVPNetworkExtended.xlsx'

def highlight_date(s):
    return np.where(pd.to_datetime(s) < campaignStartDate, 'background-color: yellow;', None)

def highlight_name(s, v=None):
    return np.where(pd.to_datetime(v) < campaignStartDate, 'background-color: yellow;', None)

def highlight_eid(s, role = None, v=None):
    pred = np.where((pd.to_datetime(v) < campaignStartDate) & (role == 'Organizer'), True, False)
    return np.where(pred, 'background-color: yellow;', None)

### Note that we are writing a multiindex, so we call "map_index."  For a regular dataframe it would be "map."
### You create the styler and call "to_excel" on it.
### see https://pandas.pydata.org/docs/user_guide/style.html for more documentation
with pd.ExcelWriter('test.xlsx' ) as writer:
    workbook = writer.book
    worksheet = workbook.create_sheet('Sheet1')
    multi.style.map_index(highlight_cells, axis = 'index', level = [1,2] ).to_excel(writer, "Sheet1",  engine='xlsxwriter')
    
    
## If you are not writing a multiindex, you can just use the aooly() and map() methods.  Note here the chain of .apply()
## calls, one call per column of the output spreadsheet. You can only format cells in a row where the predicate is true.
## To gat around that, try map() instead of aply().    
with pd.ExcelWriter(out_file) as writer:    
    workbook = writer.book
    for key, value in ids_to_names.items():
        worksheet = workbook.create_sheet(value)
        director_df = WriteTreeForDirector(key, leaders, voters)
        director_df = AddParentNames(director_df)
        
        ## the multiindex organized the data 
        ## nicely even we throw it away in the next step
        multi = director_df.set_index(['ParentRole','ParentEID','ParentName'])\
            .sort_values(by = ['ParentRole','ParentName', 'Role','LastUsedEmpowerAt'],\
            ascending = [True, True, True, False])
            
        ## seems to be hard to style a multiindex, for now just collapse it 
        multi.reset_index(inplace=True)
        multi.style.apply(highlight_date, axis = 1, subset=['LastUsedEmpowerAt'])\
                .apply(highlight_name,  v=multi['LastUsedEmpowerAt'], axis = 0, subset=['FullName'])\
                .apply(highlight_eid, role = multi['Role'], v=multi['LastUsedEmpowerAt'], axis = 0, subset=['EID'])\
                .to_excel(writer,value,  engine='xlsxwriter', index = False)
        
        print('wrote tree for:', value)    
    
    
    