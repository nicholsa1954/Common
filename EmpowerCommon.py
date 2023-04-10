
import argparse	
import re
from operator import and_, or_, contains
from functools import reduce
from itertools import groupby

	
def ParseArgs():
    ## For future reference, a slicker way to parse args. Shows required vs. optional tricks:
    ## https://stackoverflow.com/questions/24180527/argparse-required-arguments-listed-under-optional-arguments 

    # Parse the command line:
    parser = argparse.ArgumentParser(description = "A program to read and process a tree structure file exported from Empower.") 
    optional = parser._action_groups.pop() # Edited this line
    required = parser.add_argument_group('required arguments') 
    required.add_argument("-i", "--infile",  type=str, nargs=1, metavar="input_file", help="Opens and reads from the specified file.", required=True)
    required.add_argument("-o", "--outfile", type=str, nargs=1, metavar="output_file", help="Opens and writes to the specified file.", required=True)
   
    optional.add_argument("-n", "--name", type = str, nargs='+', metavar="organizer_name", help="Print tree for organizer with given name.", default=[])
    optional.add_argument("-id", type = str, nargs='+', metavar="organizer_id", help="Print tree for organizers with given id.", default=[])
    optional.add_argument("-ctas", "--ctaoutfile", type = str, nargs=1, metavar="cta_file", help="Opens and writes call-to-action results to the specified file.", default=[""])
    optional.add_argument("-s", "--spanish", action="store_true", help="If set, prints output in Spanish.", default=False)
    optional.add_argument("-v", "--verbose", action="store_true", help="If set, prints more verbose output.")
    parser._action_groups.append(optional)
    return parser.parse_args()

def WriteEnglishHeader(fh, idStrings):
    fh.write("\n Names are arranged hierarchically, indentation shows organizer -> vocero relationship.\n")
    fh.write(" Organizer and voter numbers are cumulative --\n")
    fh.write(" the organizer/voter count for an organizer/vocero is the sum of their\n")
    fh.write(" organizer/voter count and the organizer/voter count of\n") 
    fh.write(" all of the organizers/voceros below them.\n")
    fh.write(" Activation numbers are non-cumulative and show activation by a vocero of a personal\n")
    fh.write(" contact, for any call to action since the beginning of the program.\n")
    if idStrings:
        fh.write(" Voceros are listed below organizers, voters are listed below voceros.\n")
    fh.write(" 'Supervoceros' are organizers who have more than 0 organizers below them.\n\n")
    fh.write(" {:<46} {:>5} {:>18} {:>9} {:>16}".format("Name, ID",  "Phone", "Organizers", "Voters", "Activation\n"))
    fh.write(" {:<46} {:>13} {:>10} {:>10} {:>15} {:>1}".format(46*'_', 13*'_', 10*'_', 8*'_', 12*'_','\n' ))

def WriteSpanishHeader(fh, idStrings):
    fh.write("\n Los nombres están ordenados jerárquicamente, la sangría muestra relación organizador -> vocero.\n")
    fh.write(" Los números de organizadores y votantes son acumulativos --\n")
    fh.write(" el recuento de organizadores/votantes para un organizador/vocero es la suma de su\n")
    fh.write(" recuento de organizadores/votantes y el recuento de organizadores/votantes\n") 
    fh.write(" de todos los organizadores/voceros abajo.\n")
    if idStrings:
        fh.write(" Voceros se enumeran a continuación organizadores, los votantes se enumeran a continuación voceros.\n")
    fh.write(" 'Supervoceros' son organizadores que tienen más de 0 organizadores debajo de ellos.\n\n")
    fh.write(" {:<46} {:>5} {:>18} {:>11}".format("Nombre, ID",  "Teléfono", "Organizadores", "Votantes\n"))
    fh.write(" {:<46} {:>13} {:>10} {:>10} {:>1}".format(46*'_', 13*'_', 13*'_', 8*'_','\n' ))	

def containsAny(str, set):
    return reduce(or_, map(contains, len(set)*[str], set))

def containsDigit(str):
    return re.search('\d', str)

def tooManyChars(str):
    groups = groupby(str)
    result = [(label, sum(1 for _ in group) ) for label, group in groups]
    for item, count in result:
        return count >= 3

def FilterContactForValidData(currentContact):
    listBadFirstNameCharacters = ['.', '?', '(', ')', '<', '!', '`']
    listBadLastNameCharacters = ['?', '<', '!', '*']
    # contains any digit
    # 3 or more of any character
    # only 1 character
    listBadFirstNames = ['NoFirstName', 'Seiu', 'Hna', 'Hno', 'Br', 'Brother', 'Sister', 'Mn', 'Grandpa', 'Grandma', 'Tia', 'Tio', 'Pastor', 'Ald', 'Coach','Mr', 'Mrs', 'Ms', 'Sr', 'Jr', 'Sra', 'Miss','Father', 'Com', 'Hermano', 'Empowered', 'Mom', 'Dad', 'Ma', 'Bro', 'Mommy', 'Uncle', 'Aunt', 'Auntie']
    listBadLastNames = ['NoLastName', 'Seiu', 'Mash', 'Daca', 'Dad', 'Coach', 'Matc']

    countMissingFirstName = 0
    countMissingLastName = 0
    countNonASCIIFirstName = 0
    countNonASCIILastName = 0
    countMissingPhoneNumber = 0
    countVANMatched = 0

    firstName = currentContact.GetFirstName()
    lastName = currentContact.GetLastName()
    if currentContact.HasVANMatch():
        countVANMatched = 1
    elif not currentContact.GetPhone():
        countMissingPhoneNumber = 1
    elif not firstName or containsAny(firstName, listBadFirstNameCharacters) or containsAny(firstName, listBadFirstNames) or containsDigit(firstName) or tooManyChars(firstName):
        countMissingFirstName = 1
    elif not lastName or containsAny(lastName, listBadLastNameCharacters) or containsAny(lastName, listBadLastNames) or containsDigit(lastName) or tooManyChars(lastName) or len(lastName) <= 2:
        countMissingLastName = 1
    elif (re.sub('[ -~]', '', firstName)) != "":
        countNonASCIIFirstName = 1
    elif (re.sub('[ -~]', '', lastName)) != "":
        countNonASCIILastName = 1

    return [countVANMatched, countMissingPhoneNumber, countMissingFirstName, countMissingLastName, countNonASCIIFirstName, countNonASCIILastName]