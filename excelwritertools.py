### this is how to do styling:

def highlight_cells(s):
    return "background-color: yellow;" if s in departed_eids or s.strip() in departed_names else ""

### Note that we are writing a multiindex, so we call "map_index."  For a regular dataframe it would be "map."
### You create the styler and call "to_excel" on it.
### see https://pandas.pydata.org/docs/user_guide/style.html for more documentation
with pd.ExcelWriter('test.xlsx' ) as writer:
    workbook = writer.book
    worksheet = workbook.create_sheet('Sheet1')
    multi.style.map_index(highlight_cells, axis = 'index', level = [1,2] ).to_excel(writer, "Sheet1",  engine='xlsxwriter')