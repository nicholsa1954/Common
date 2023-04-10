# -*- coding: utf-8 -*-

import pandas as pd
from pandas.testing import assert_frame_equal
import unittest
from setoperations import SetDifference, SetIntersection

from setoperations import SetUnion, SetSymmetricDifference
from setoperations import FilterToInclude, FilterToExclude, Query

ydf = pd.DataFrame({'x1':['A', 'B', 'C'], 'x2': [1,2,3]})
zdf = pd.DataFrame({'x1':['B', 'C', 'D'], 'x2': [2,3,4]})

df1 = {'A1': ['a','b','c','d'],'B': ['Geeks', 'For', 'efg', 'ghi']} 
df2 = {'A2': ['a','b','p','q' ],'B': ['Geeks', 'For', 'abc', 'cde'],
       'C':['Nikhil', 'Rishabh', 'Rahul', 'Shubham']} 

pdf = pd.DataFrame({'A1': ['a','b','c','d'],'B': ['Geeks', 'For', 'efg', 'ghi']})
qdf = pd.DataFrame({'A2': ['a','b','p','q' ],'B': ['Geeks', 'For', 'abc', 'cde'],
       'C':['Nikhil', 'Rishabh', 'Rahul', 'Shubham']})

rdf = pd.DataFrame({'A': [1,2,3,4],'B': ['Geeks', 'For', 'efg', 'ghi']})
sdf = pd.DataFrame({'A': [1,2,3,4],'B': ['Geeks', 'For', 'abc', 'cde'],
       'C':['Nikhil', 'Rishabh', 'Rahul', 'Shubham']})

adf = pd.DataFrame({'x1':['A', 'B', 'C'], 'x2': [1,2,3]})
bdf = pd.DataFrame({'x1':['A', 'B', 'D'], 'x3': [True, False, True]})

df3 = pd.DataFrame({'Name':['Vikram','John', 'Alex','Paul','Andrew','Rafel' ], 
'Age':[28,39,21,50,35,43], 
'Department':['HR', 'Finance','IT','HR','IT','IT'], 
'Country':['USA','India','Germany','USA','India','India'] }) 

"""
1. open a Windows PowerShell terminal
2. usage: 'python -m unittest test_setoperations.py'
"""
class TestSetOperation(unittest.TestCase):
    
    def test_SetIntersection0(self):
        result = pd.DataFrame({'x1':['B','C'], 'x2': [2,3]})
        assert_frame_equal(SetIntersection(ydf,zdf), result)

    def test_SetIntersection1(self):
        result = pd.DataFrame({'x1':['B','C'], 'x2_x': [2,3], 'x2_y': [2,3]})
        assert_frame_equal(SetIntersection(ydf,zdf, on='x1'), result)

    ##https://www.geeksforgeeks.org/intersection-of-two-dataframe-in-pandas-python/
    def test_SetIntersection2(self):
        result = pd.DataFrame({'A1':['a','b'], 'B_x': ['Geeks','For'], 'A2': ['a','b'],\
                               'B_y':['Geeks','For'], 'C':['Nikhil', 'Rishabh']})
        assert_frame_equal(SetIntersection(pdf, qdf, how='inner', left_on='A1', right_on = 'A2'), result)

    def test_SetIntersection3(self):
        result = pd.DataFrame({'A':[1,2], 'B':['Geeks', 'For'], 'C':['Nikhil', 'Rishabh']})
        assert_frame_equal(SetIntersection(rdf, sdf, how='inner', on=['A', 'B']), result)

    def test_SetIntersectionThrows(self):        
        self.assertRaises(ValueError, SetIntersection, ydf, zdf, foo='x1')
        
    def test_SetUnion(self):
        result = pd.DataFrame({'x1':['A','B','C','D'], 'x2': [1,2,3,4]})
        assert_frame_equal(SetUnion(ydf,zdf), result)  
        
    def test_SetDifference0(self):
        result = pd.DataFrame({'x1':['A'], 'x2': [1]})
        assert_frame_equal(SetDifference(ydf,zdf), result)

    def test_SetDifferenceThrows(self):        
        self.assertRaises(ValueError, SetIntersection, ydf, zdf, foo='x1')        

    def test_SetDifference1(self):       
        result = pd.DataFrame({'x1':['D'], 'x2': [4]})
        assert_frame_equal(SetDifference(zdf,ydf), result)  

    def test_SetSymmetricDifference(self):
        result = pd.DataFrame({'x1':['A','D'], 'x2': [1,4]})
        assert_frame_equal(SetSymmetricDifference(ydf,zdf), result) 

    def test_FilterToInclude(self):
        result = pd.DataFrame({'x1':['A', 'B'], 'x2': [1,2]})
        assert_frame_equal(FilterToInclude(adf, bdf, "x1"), result)

    def test_FilterToExclude(self):
        result = pd.DataFrame({'x1':['C'], 'x2': [3]})
        assert_frame_equal(FilterToExclude(adf, bdf, "x1"), result)

    def test_Query0(self):
        result = pd.DataFrame({'Name':[ 'Alex','Andrew','Rafel' ], 
        'Age':[21,35,43], 
        'Department':['IT','IT','IT'], 
        'Country':['Germany','India','India'] })
        assert_frame_equal(Query(df3, 'Department == "IT"'), result)


if __name__ == '__main__':
    unittest.main()
