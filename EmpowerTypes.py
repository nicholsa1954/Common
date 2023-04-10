import phonenumbers
import time
import collections
import csv
from datetime import date
import sys

sys.path.append('..')
from EmpowerCommon import FilterContactForValidData

def split_n_chunks(string, words_per_chunk):
    s_list = string.split()
    pos = 0
    while pos < len(s_list):
        result = ' '.join(s_list[pos:pos+words_per_chunk])
        yield result
        pos += words_per_chunk

class Region:
    def __init__(self, record):
        self.m_Id = record['id']
        self.m_Name = record['name']
        self.mInviteCode = record['inviteCode']
        self.m_CtaId = record['ctaId']
        self.m_OrganizationId = record['organizationId']
        self.m_Description = record['description']

    def GetCtaId(self):
        return self.m_CtaId

    def GetId(self):
        return self.m_Id

    def GetName(self):
        return self.m_Name


class Question:
    def __init__(self, dict):
        self.m_Options = {}
        self.m_Type = dict['type']
        self.m_Key = dict['key']
        self.m_Text = dict['text']
        options = dict['options'] # a list, so should be ordered...
        for option in options:
            if option: self.m_Options[option] = 0 # a histogram.  Key is string value for option, value is number of occurrences. Some keys are ''
        self.m_Values = []
        self.m_SurveyQuestionVanId = 0
        if 'values' in dict.keys():
            for value in dict['values']:
                self.m_Values.append(value)
        if 'surveyQuestionVanId' in dict.keys():
            self.m_SurveyQuestionVanId = dict['surveyQuestionVanId']
        self.m_NumNullAnswers = 0
        self.m_Notes = []

    def Print(self, length, fh):
        split_list = list(split_n_chunks(self.m_Text, length ))
        fh.write("{} {}".format("    Question", str(self.m_Key)+ ": "))
        for item in split_list:
            fh.write(item + '\n')

    def GetOptions(self):
        return self.m_Options

    def GetNumAnswers(self):
        result = 0
        for key in self.m_Options:
            result += self.m_Options[key]
        return result

    def GetNotes(self):
        return self.m_Notes

class Cta:   
    def __init__(self, record):
        self.m_DictQuestions = dict()
        self.m_Id = record['id']
        self.m_Name = record['name']
        self.m_InstructionsHtml = record['instructionsHtml']
        self.m_Created =  time.strftime("%Y-%m-%d",time.gmtime(int(record['createdMts']/1000)))
        self.m_OrganizationId = record['organizationId']
        self.m_RegionIds = []
        if 'regionIds' in record.keys():
            for region in record['regionIds']:
                self.m_RegionIds.append(region)
        self.m_IsIntroCta = record['isIntroCta']
        for question in record['questions']:
            self.m_DictQuestions[question['key']] = Question(question)
        self.m_ctaResultList = []  

    def AddCtaResult(self, ctaResult):
        self.m_ctaResultList.append(ctaResult)
        #self.m_Notes.add(ctaResult.GetNotes())
        keys = self.m_DictQuestions.keys()
        for key in keys:
            question = self.m_DictQuestions[key]
            optionDict = question.GetOptions()
            answers = ctaResult.GetAnswers()
            if str(key) in answers.keys():
                answer = answers[str(key)]  
                if answer:
                     ## need to fix the answer 'Yes/Si' or 'Yes / Si' -- convert to something generic
                    alphanumeric_filter = filter(str.isalnum, answer)
                    compressed_answer = "".join(alphanumeric_filter).lower()
                    found = False
                    for optkey in optionDict.keys(): #try to map the answer into one of the options for the question            
                        alphanumeric_filter = filter(str.isalnum, optkey)
                        compressed_key = "".join(alphanumeric_filter).lower()
                        if (compressed_answer in compressed_key):
                            optionDict[optkey] += 1
                            found = True
                            break               
                    if not found: #can't map it -- treat it as 'other', save it, and start a count
                        optionDict[answer] = 1
                else: #answers[str(key)] is None -- null or empty
                    question.m_NumNullAnswers += 1

    def GetId(self):
        return self.m_Id

    def GetName(self):
        return self.m_Name  

    def GetNumCtaResults(self):
        return len(self.m_ctaResultList)

    def Print(self, fh):
        keys = self.m_DictQuestions.keys()
        fh.write("{} {}".format("CTA Id:", str(self.m_Id)+'\n'))
        fh.write("{} {}".format("CTA name:", self.GetName()+'\n'))
        for key in keys:
            self.m_DictQuestions[key].Print(len(self.m_Name.split()), fh)      
        fh.write("{} {}".format("Respondent count:", str(self.GetNumCtaResults())+'\n'))
        for key in keys:
            question = self.m_DictQuestions[key]
            fh.write("{} {} {} {}" .format( "Question", str(key)+':', "responses", str(question.GetNumAnswers())+'\n') )
            optionDict = question.GetOptions()
            for optkey in optionDict.keys():
                fh.write("{} {} {}".format("   ", optkey + ":", str(optionDict[optkey]) +'\n'))
            fh.write("{} {}".format("    Null or empty:", str(question.m_NumNullAnswers) + '\n'))
            if question.GetNotes():
                fh.write(question.GetNotes())
            fh.write('\n')
        fh.write('\n')
    
class CtaResult:
    def __init__(self,record):
        self.m_ProfileEid = record['profileEid'].strip()
        self.m_CtaId = record['ctaId']
        self.m_Contacted =  time.strftime("%Y-%m-%d",time.gmtime(int(record['contactedMts']/1000)))
        self.m_DictAnswers = record['answers']
        if record['notes']: self.m_Notes = record['notes']
        else: self.m_Notes = ''

    def GetCtaId(self):
        return self.m_CtaId

    def GetContactId(self):
        return self.m_ProfileEid 

    def GetContacted(self):
        return self.m_Contacted

    def GetAnswers(self):
        return self.m_DictAnswers

    def GetNotes(self):
        return self.m_Notes

class Contact:
    def __init__(self, record, recordType):
        if recordType == '.csv':
            self.__initFromCSV(record)
        else:
            self.__initFromJSON(record)

    def __initFromCSV(self, record):
        self.m_EID = record['EID'].strip()
        self.m_ParentEID = record['Parent EID'].strip()
        self.m_Role = record['Role'] 
        self.m_RegionId = 0
        self.m_RegionName = record['Region Name'] 
        self.m_FirstName = record['First Name'].title() 
        if 'DELETED' in record['Last Name']:
            self.m_LastName = record['Last Name']
        else:
            self.m_LastName = record['Last Name'].title()
        self.m_FullName = self.m_FirstName.lower() + self.m_LastName.lower()
        self.m_Email = record['Email'] 
        self.m_Phone = self.ParsePhone(record['Phone']) 
        self.m_City = record['City'] 
        if record ['State']: self.m_State = record['State']  
        else:  self.m_State = "WI"
        self.m_ZipCode = record['Zip Code'] 
        self.m_Address = record['Address'] 
        self.m_Address2 = record['Address Line 2'] 
        self.m_VanId = record['vanId']
        self.m_CampaignVanId = record['myCampaignVanId']
        self.m_Created =  self.ParseCreated(record['Created At']) 
        self.m_CurrentCtaId = 0
        self.m_Cta = None

    def __initFromJSON(self, record):
        self.m_EID = record['eid'].strip()
        if record['parentEid']: self.m_ParentEID = record['parentEid'].strip()
        else: self.m_ParentEID = ""
        if self.m_EID == self.m_ParentEID:
            self.m_ParentEID = ""
            print(record['lastName'].title())
        self.m_Role = record['role']
        if record['regionId']: self.m_RegionId = record['regionId'] 
        else: self.m_RegionId = 0
        self.m_RegionName = ""
        if record['firstName']:
            self.m_FirstName = record['firstName'].title()
        else:
            self.m_FirstName = "NoFirstName"
        if record['lastName']:
            if 'DELETED' in record['lastName']:
                self.m_LastName = record['lastName']
            else:
                self.m_LastName = record['lastName'].title()
        else:
            self.m_LastName = "NoLastName"
        self.m_FullName = self.m_FirstName.lower() + self.m_LastName.lower()
        self.m_Email = record['email']
        self.m_Phone = self.ParsePhone(record['phone'])
        if record['city']: self.m_City =  record['city']
        else: self.m_City =  "NoCity"
        if record['state']: self.m_State = record['state'] 
        else:  self.m_State = "WI"
        self.m_ZipCode = record['zip']
        self.m_Address = record['address']
        self.m_Address2 =  record['address2']
        self.m_VanId = record['vanId']
        self.m_CampaignVanId = record['myCampaignVanId']
        self.m_Created =  record['createdMts'] ##time.strftime("%Y-%m-%d",time.gmtime(int(record['createdMts']/1000)))
        self.m_CurrentCtaId = record['currentCtaId']
        self.m_Cta = None
        self.m_nCountActiveCtaResponses = -1
        self.m_nCountCurrentCtaResponses = -1
        self.m_bRespondedToAnyCta = -1
        self.m_bRespondedToActiveCta = -1
        self.m_bRespondedToCurrentCta = -1

    def AddCta(self, Cta):
        self.m_Cta = Cta

    def CompareNames(self, contact):
        return self.m_FullName == contact.m_FullName

    def GetAddress(self):
        return self.m_Address

    def GetCta(self):
        return self.m_Cta

    def GetActiveCtaResponseCount(self):
        return self.m_nCountActiveCtaResponses

    def GetDaysSinceCreatedAsInt(self):
        created = date.fromtimestamp(self.m_Created/1000)
        now = date.today()
        elapsed = now - created
        return elapsed.days

    def GetDaysSinceCreated(self):
        created = date.fromtimestamp(self.m_Created/1000)
        now = date.today()
        elapsed = now - created
        return (str(elapsed.days) + " days")

    def GetCity(self):
        return self.m_City

    def GetCurrentCtaId(self):
        return self.m_CurrentCtaId

    def GetCurrentCtaResponseCount(self):
        return self.m_nCountCurrentCtaResponses

    def GetContactID(self):
        return self.GetEID()

    def GetEID(self):
        return self.m_EID

    def HasCtaResults(self):
        if not self.m_Cta: return False
        return self.GetCta().GetNumCtaResults() > 0

    def GetParentEID(self):
        return self.m_ParentEID

    def GetPhone(self):
        return self.m_Phone;

    def GetRegionId(self):
        return self.m_RegionId

    def GetRegionName(self):
        return self.m_RegionName

    def GetRole(self):
        return self.m_Role.lower()

    def GetState(self):
        return self.m_State

    def GetTimeCreated(self):
        return time.strftime("%Y-%m-%d",time.gmtime(int(self.m_Created/1000)))

    def GetVANID(self):
        if not self.m_VanId:
            return ""
        return self.m_VanId

    def GetZipCode(self):
        return self.m_ZipCode

    def GetFirstName(self):
        return self.m_FirstName

    def GetLastName(self):
        return self.m_LastName

    def GetName(self):
        return self.m_FirstName + ' ' + self.m_LastName + ' ' + "(" + self.GetContactID() + ")"

    def GetFullName(self):
        return self.m_FullName

    def HasVANMatch(self):
        return self.m_VanId != None

    #used for .csv file only
    def ParseCreated(self, string):
        if not string:
            return ""
        [date,time] = string.split('T')
        return date

    #used for .csv and .json file
    def ParsePhone(self, phone):
        if not phone: return ''
        try:
            phone = phonenumbers.parse(phone, "US")
        except:
            phone = 'The string supplied did not seem to be a phone number'
        try:
            if not phonenumbers.is_possible_number(phone):
                phone = 'Listed number is not possible, please check'
            elif not phonenumbers.is_valid_number(phone):
                phone = 'Listed number is not valid, please check'
        except(AttributeError):
            phone = "Raised an AttributeError"
        try:
            phone = phonenumbers.format_number(phone, phonenumbers.PhoneNumberFormat.NATIONAL)
        except:
            phone = 'this is a mess!'
        return phone

    def Print(self, dict, fh, verbose, depth):
        label = depth*'-'+" Voter:"
        ofs = len(label)
        fh.write(" {a:{o}} {b:<35} {c:<18} {d:<8} {e:<12}".format(a=label, o=ofs, b=self.GetName(),
        c=self.GetPhone(), d="Created", e=self.GetTimeCreated())) 
        parentEid = self.GetParentEID()
        if verbose:
            while parentEid in dict.keys():
                parent = dict[parentEid]
                fh.write("{} {}".format(" -> ", parent.GetName()))
                parentEid = parent.GetParentEID()
        fh.write("\n")
        return self.GetFullName()

    def PrintUnactivatedToCSV(self, dict, index, csvwriter, depth):
        row = ['\''+depth*'*'+' '+ str(index)+ '. ' + self.GetFirstName()+'\'',  self.GetLastName(), self.GetEID(), self.GetVANID(), self.GetPhone(), self.GetRegionName(),
               " "," ", " ", " ", " ", " "," ",
               self.GetTimeCreated(), self.GetDaysSinceCreated()] 
        csvwriter.writerow(row)


    #Headers = ['First Name', 'Last Name', 'Contact ID', 'Phone', 'Unmatched Direct Contacts', 'Matched Direct Contacts', 'Total Direct Contacts']
    def PrintUnmatchedToCSV(self, dict, index, csvwriter, depth):
        row = ['\''+depth*'*'+' '+ str(index)+ '. ' + self.GetFirstName()+'\'',  self.GetLastName(), self.GetEID(), self.GetVANID(), self.GetPhone(), " ", " ", " "]
        csvwriter.writerow(row)
      
    def SetRegionName(self, name):
        self.m_RegionName = name

class Organizer (Contact):
    def __init__(self, record, recordType):
        Contact.__init__(self, record, recordType)
        self.m_ContactDict = {}
        self.m_OrganizerDict = {}
        self.m_ContactActivationRate = -1.0
        self.m_ActivatedContactCountAnyCtas = -1
        self.m_ActivatedContactCountActiveCtas = -1
        self.m_ActivatedContactCountCurrentCtas = -1
        self.m_MapAnyResultResponseRateToOrganizer = collections.OrderedDict()
        self.m_MapActiveResultResponseRateToOrganizer = collections.OrderedDict()
        self.m_MapCurrentResultResponseRateToOrganizer = collections.OrderedDict()
        self.m_ListInactiveOrganizers = []

        try:
            if record['lastUsedEmpowerMts']:
                self.m_LastUsedEmpower = record['lastUsedEmpowerMts'] # time.strftime("%Y-%m-%d",time.gmtime(int(record['lastUsedEmpowerMts']/1000)))
            else: self.m_LastUsedEmpower = "Unknown/Never"
        except: self.m_LastUsedEmpower = "Unknown/Never"

    def AddContact(self, Contact):
        self.m_ContactDict[Contact.m_EID] = Contact

    def AddOrganizer(self, Contact):
        self.m_OrganizerDict[Contact.m_EID] = Contact

    def GetContactID(self):
        #if not self.GetEID():
        #    print('GetContactID failure in:', self.GetFirstName(), self.GetLastName())
        try:
            if '-' in self.GetEID():
                if len(self.GetEID().split('-')) == 3:
                    return self.GetEID().split('-')[2]
                if len(self.GetEID().split('-')) == 2:
                      return self.GetEID().split('-')[1]
                else: return self.GetEID()
        except ValueError as err:
            print("Value error: {0}".format(err))
            print('GetContactID failure in:', self.m_FirstName, self.m_LastName, self.GetEID())
        except UnboundLocalError as err:
            print("UnboundLocalError error: {0}".format(err))
            print('GetContactID failure in:', self.m_FirstName, self.m_LastName, self.GetEID())
        #print("GetContactID Failed:", self.m_FirstName, self.m_LastName, self.GetEID())
        return self.GetEID()

    def GetContactActivationRateAnyCtas(self):
        if self.GetDirectContactCount() == 0:
            return 0.0
        return int(self.GetContactCountAnyCtas()/self.GetDirectContactCount() * 100.0) /100.0

    def GetContactActivationRateActiveCtas(self):
        if self.GetDirectContactCount() == 0:
            return 0.0
        return int(self.GetContactCountActiveCtas()/self.GetDirectContactCount() * 100.0) /100.0

    def GetContactActivationRateCurrentCtas(self):
        if self.GetDirectContactCount() == 0:
            return 0.0
        return int(self.GetContactCountCurrentCtas()/self.GetDirectContactCount() * 100.0) /100.0

    def GetContactActivationString(self):
        return str(self.GetContactCountActiveCtas()) + '/' + str(self.GetDirectContactCount())

    def GetContactCountAnyCtas(self):
        #return len(self.m_ContactDict) - self.m_UnactivatedContactCount
        return self.m_ActivatedContactCountAnyCtas 

    def GetContactCountActiveCtas(self):
        #return len(self.m_ContactDict) - self.m_UnactivatedContactCount
        return self.m_ActivatedContactCountActiveCtas 

    def GetContactCountCurrentCtas(self):
        return self.m_ActivatedContactCountCurrentCtas

    def GetOrganizerCount(self):
        count = 0
        for key in self.m_OrganizerDict.keys():
            count += self.m_OrganizerDict[key].GetOrganizerCount()
        return count + len(self.m_OrganizerDict)

    def GetContactCount(self):
        count = 0
        for key in self.m_OrganizerDict.keys():
            count += self.m_OrganizerDict[key].GetContactCount()
        return count + len(self.m_ContactDict)

    def GetContactDictionary(self):
        return self.m_ContactDict

    def GetDaysSinceLastLogin(self):
        if self.m_LastUsedEmpower == "Unknown/Never":
            return ""
        lastLogin = date.fromtimestamp(self.m_LastUsedEmpower/1000)
        now = date.today()
        elapsed = now - lastLogin
        return (str(elapsed.days) + " days")

    def GetDaysSinceLastLoginAsInt(self):
        if self.m_LastUsedEmpower == "Unknown/Never":
            return 100000  #just needs to be a really big number
        lastLogin = date.fromtimestamp(self.m_LastUsedEmpower/1000)
        now = date.today()
        elapsed = now - lastLogin
        return elapsed.days

    def GetDirectContactCount(self):
        return len(self.m_ContactDict)

    def GetParent(self):
        if self.GetParentEID() in self.m_OrganizerDict.keys():
            return self.m_OrganizerDict[GetParentEID()]
        return None

    #used for .csv file only
    def ParseLastUsedEmpower(self, string):
        if not string:
            return ""
        if 'T' in string:
            [date,time] = string.split('T')
            return date
        return string
            
    def Print(self, dict, fh):
        fh.write(" {:<11} {:<35} {:<18} {:<4} {:<4} {:<8} {:<12}".format( " Organizer:", 
        self.GetName(), self.GetPhone(), self.GetOrganizerCount(), self.GetContactCount(), "Created", self.m_Created))
        parentEid = self.GetParentEID()
        while parentEid in dict.keys():
            parent = dict[parentEid]
            fh.write("{} {}".format(" -> ", parent.GetName()))
            parentEid = parent.GetParentEID()
        fh.write("\n")

    def PrintNumbers(self):
        print(self.GetName(), "\t", self.GetOrganizerCount(), "\t", self.GetContactCount())

    def SetActivatedContactCountAnyCtas(self, count):
        self.m_ActivatedContactCountAnyCtas = count

    def SetActivatedContactCountActiveCtas(self, count):
        self.m_ActivatedContactCountActiveCtas = count

    def SetActivatedContactCountCurrentCtas(self, count):
        self.m_ActivatedContactCountCurrentCtas = count

    def GetLastUsedEmpower(self):
        if self.m_LastUsedEmpower == "Unknown/Never":
            return self.m_LastUsedEmpower
        return time.strftime("%Y-%m-%d",time.gmtime(int(self.m_LastUsedEmpower/1000)))

    def PrintTree(self, dict, fh, verbose, startAtRoot):
        ParentEID = self.GetParentEID()
        if startAtRoot and (not ParentEID or ParentEID not in dict.keys()):
            self.__PrintTree(dict, fh, verbose)
            fh.write("\n")
            return []
        elif not startAtRoot: #start at self
            voterNames = self.__PrintTree(dict, fh, verbose, True)
            fh.write("\n")
            return voterNames

    def __PrintTree(self, dict, fh, verbose, showVoters = False, depth=0):
        ParentEID = self.GetParentEID()
        keys = dict.keys()
        voterNames = []
        if verbose:
           if ParentEID not in keys or not ParentEID:
                fh.write(" {:<45} {:>15} {:>5} {:>12} {:>10.2f} {:<9}".format(depth*'-'+ self.GetName(), self.GetPhone(), 
                self.GetOrganizerCount(), self.GetContactCount(), self.GetContactActivationRateActiveCtas(), self.GetContactActivationString()))
                fh.write("  is a terminal node.\n")
           else: 
                fh.write(" {:<45} {:>15} {:>5} {:>12} {:>10.2f} {:<9}".format(depth*'-'+ self.GetName(), self.GetPhone(), 
                self.GetOrganizerCount(), self.GetContactCount(), self.GetContactActivationRateActiveCtas(), self.GetContactActivationString()))
                fh.write( "  -> ")
           while ParentEID and ParentEID in keys:
                Parent = dict[ParentEID]
                ParentEID = Parent.GetParentEID()
                if ParentEID not in keys or not ParentEID:
                    fh.write(Parent.GetName() + "\n")
                else:
                    fh.write(Parent.GetName() + "-> ")
        else:
            fh.write(" {:<45} {:>15} {:>5} {:>12} {:>10.2f} {:<9}".format(depth*'-'+ self.GetName(), self.GetPhone(), 
            self.GetOrganizerCount(), self.GetContactCount(), self.GetContactActivationRateActiveCtas(), self.GetContactActivationString()))
            fh.write("\n")

        #for key in self.m_OrganizerDict.keys():
        #    self.m_OrganizerDict[key].__PrintTree(dict, fh, verbose, showVoters, depth+3)
        keys = reversed(sorted(self.m_MapActiveResultResponseRateToOrganizer.keys())) 
        for key in keys:
            OrganizerSet = self.m_MapActiveResultResponseRateToOrganizer[key]   
            for organizer in OrganizerSet:
                organizer.__PrintTree(dict, fh, verbose, showVoters, depth+3)
        for organizer in self.m_ListInactiveOrganizers:
             organizer.__PrintTree(dict, fh, verbose, showVoters, depth+3)
        if showVoters:
            for key3 in self.m_ContactDict.keys():
                voterNames.append(self.m_ContactDict[key3].Print(dict, fh, verbose, depth+3))
            return voterNames

##########################
    def PrintTreeToCSV(self, dict, csvwriter, startAtRoot):
        if self.m_Role == 'deleted': return
        ParentEID = self.GetParentEID()
        if startAtRoot and (not ParentEID or ParentEID not in dict.keys()):
            self.__PrintTreeToCSV(dict, csvwriter)
            row = [" "]
            csvwriter.writerow(row)
            return []
        elif not startAtRoot: #start at self
            voterNames = self.__PrintTreeToCSV(dict, csvwriter, True)
            return voterNames

    def __PrintTreeToCSV(self, dict, csvwriter, showVoters = False, depth=0):
        ParentEID = self.GetParentEID()
        keys = dict.keys()
        voterNames = []

        row = ['\''+depth*'-'+self.GetFirstName()+'\'',  self.GetLastName(), self.GetEID(), self.GetPhone()]
        csvwriter.writerow(row)

        keys = self.m_OrganizerDict.keys()
        for key in keys:
            self.m_OrganizerDict[key].__PrintTreeToCSV(dict, csvwriter, showVoters, depth+3)
        #if showVoters:  #todo: need an override for .csv output
        #    for key3 in self.m_ContactDict.keys():
        #        voterNames.append(self.m_ContactDict[key3].Print(dict, fh, verbose, depth+3))
        #    return voterNames     

##########################
    def PrintUnactivatedContactsToCSV(self, dict, csvwriter, startAtRoot):
        if self.m_Role == 'deleted': return []
        ParentEID = self.GetParentEID()
        if startAtRoot and (not ParentEID or ParentEID not in dict.keys()):
            self.__PrintUnactivatedContactsToCSV(dict, csvwriter)
            row = [" "]
            csvwriter.writerow(row)
            return []
        elif not startAtRoot: #start at self
            voterNames = self.__PrintUnactivatedContactsToCSV(dict, csvwriter)
            return voterNames

    def __PrintUnactivatedContactsToCSV(self, dict, csvwriter, depth = 0):
        listUnactivatedContacts = []

        for key in self.m_ContactDict.keys():
            contact = self.m_ContactDict[key]
            if contact.m_bRespondedToAnyCta == 1: continue
            assert(contact.m_bRespondedToAnyCta == 0)
            listUnactivatedContacts.append(contact)

        assert(len(listUnactivatedContacts) == self.GetDirectContactCount() - self.GetContactCountAnyCtas())

        row = ['\''+depth*'-'+self.GetFirstName()+'\'',  self.GetLastName(), self.GetEID(), self.GetVANID(), self.GetPhone(), self.GetRegionName(), len(listUnactivatedContacts),
                  self.GetContactCountActiveCtas(), self.GetContactCountCurrentCtas(), self.GetDirectContactCount(), self.GetContactActivationRateAnyCtas(), 
                  self.GetLastUsedEmpower(), self.GetDaysSinceLastLogin(), self.GetTimeCreated(), self.GetDaysSinceCreated()]
        csvwriter.writerow(row)

        for key in self.m_OrganizerDict.keys():
            self.m_OrganizerDict[key].__PrintUnactivatedContactsToCSV(dict, csvwriter, depth+3)

        ndx = 1
        for contact in listUnactivatedContacts:
            contact.PrintUnactivatedToCSV(dict, ndx, csvwriter, depth+3)
            ndx += 1
    

##########################
    def PrintUnmatchedContactsToCSV(self, dict, csvwriter, startAtRoot):
        if self.m_Role == 'deleted': return
        ParentEID = self.GetParentEID()
        if startAtRoot and (not ParentEID or ParentEID not in dict.keys()):
            self.__PrintUnmatchedContactsToCSV(dict, csvwriter)
            row = [" "]
            csvwriter.writerow(row)
            return []
        elif not startAtRoot: #start at self
            voterNames = self.__PrintUnmatchedContactsToCSV(dict, csvwriter)
            return voterNames

    def __PrintUnmatchedContactsToCSV(self, dict, csvwriter, depth = 0):
        listUnmatchedContacts = []
        countMatchedDirectContacts = 0
        countBadDataContacts = 0
        for key in self.m_ContactDict.keys():
            contact = self.m_ContactDict[key]
            results = FilterContactForValidData(contact)
            if results[0] > 0:
                countMatchedDirectContacts += 1
            elif sum(results) > 0:
                countBadDataContacts += 1
            else: listUnmatchedContacts.append(contact)

        row = ['\''+depth*'-'+self.GetFirstName()+'\'',  self.GetLastName(), self.GetEID(), self.GetVANID(), self.GetPhone(), len(listUnmatchedContacts), 
               countBadDataContacts, countMatchedDirectContacts, len(self.m_ContactDict)]
        csvwriter.writerow(row)

        for key in self.m_OrganizerDict.keys():
            self.m_OrganizerDict[key].__PrintUnmatchedContactsToCSV(dict, csvwriter, depth+3)

        ndx = 1
        for contact in listUnmatchedContacts:
            contact.PrintUnmatchedToCSV(dict, ndx, csvwriter, depth+3)
            ndx += 1

    ##########################
    def PrintContactInterestToCSV(self, dict, organizerList, contactList, interest, csvwriter, startAtRoot):
        if self.m_Role == 'deleted': return
        ParentEID = self.GetParentEID()
        if startAtRoot and (not ParentEID or ParentEID not in dict.keys()):
            self.__PrintContactInterestToCSV(dict, organizerList, contactList,  interest, csvwriter)
            row = [" "]
            csvwriter.writerow(row)
            return []
        elif not startAtRoot: #start at self
            voterNames = self.__PrintContactInterestToCSV(dict, organizerList, contactList,  interest, csvwriter)
           
    def __PrintContactInterestToCSV(self, dict, organizerList, contactList, interest, csvwriter, depth = 0):
        for item in organizerList:
            row = ['\''+depth*'-'+item.GetFirstName()+'\'',  item.GetLastName(), item.GetEID(), item.GetPhone(), " ", " ", " "]
            csvwriter.writerow(row)
            depth += 3

        for item in contactList:
            dictitem = dict[item[0]]
            row = ['\''+depth*'*'+dictitem.GetFirstName()+'\'',  dictitem.GetLastName(), dictitem.GetEID(), dictitem.GetPhone(), interest, item[1], item[2]]
            csvwriter.writerow(row)

##########################
    def PrintActivationRateToCSV(self, dict, csvwriter, loginCutoff, startAtRoot):
        if self.m_Role == 'deleted': return
        if self.GetDaysSinceLastLoginAsInt() > loginCutoff: 
            #print(self.GetFirstName(), self.GetLastName(), self.GetDaysSinceLastLoginAsInt())
            return
        ParentEID = self.GetParentEID()
        if startAtRoot and (not ParentEID or ParentEID not in dict.keys()):
            self.__PrintActivationRateToCSV(dict, csvwriter, loginCutoff)
            row = [" "]
            csvwriter.writerow(row)
            return []
        elif not startAtRoot: #start at self
            voterNames = self.__PrintActivationRateToCSV(dict, csvwriter, loginCutoff, True)
            return voterNames

    def __PrintActivationRateToCSV(self, dict, csvwriter, loginCutoff, showVoters = False, depth=0):
        ParentEID = self.GetParentEID()
        keys = dict.keys()
        voterNames = []
        if self.GetDaysSinceLastLoginAsInt() > loginCutoff: return
        row = ['\''+depth*'-'+self.GetFirstName()+'\'',  self.GetLastName(), self.GetEID(), self.GetPhone(), self.GetRegionName(),
                  self.GetContactCountAnyCtas(), self.GetDirectContactCount(), self.GetContactActivationRateAnyCtas(), 
                  self.GetLastUsedEmpower(), self.GetDaysSinceLastLogin(), self.GetTimeCreated(), self.GetDaysSinceCreated()]
        csvwriter.writerow(row)

        keys = reversed(sorted(self.m_MapAnyResultResponseRateToOrganizer.keys())) 
        for key in keys:
            OrganizerSet = self.m_MapAnyResultResponseRateToOrganizer[key]
            for organizer in OrganizerSet:
                organizer.__PrintActivationRateToCSV(dict, csvwriter, loginCutoff,  showVoters, depth+3)
        for organizer in self.m_ListInactiveOrganizers:
             organizer.__PrintActivationRateToCSV(dict, csvwriter, loginCutoff, showVoters, depth+3)

        #if showVoters:  #todo: need an override for .csv output
        #    for key3 in self.m_ContactDict.keys():
        #        voterNames.append(self.m_ContactDict[key3].Print(dict, fh, verbose, depth+3))
        #    return voterNames     