# Author:: deadjakk
import json,csv,argparse,StringIO,sys
parser = argparse.ArgumentParser()
parser.add_argument("-f",help="tsv file to be parsed into a bloodhound format")
parser.add_argument("-u",help="states the file being parsed is a user file",action="store_true")
parser.add_argument("-c",help="states the file being parsed is a computer file",action="store_true")
parser.add_argument("-g",help="states the file being parsed is a group file",action="store_true")
parser.add_argument("-d",help="specify the domain (some legacy domains use different domains)")
parsed = parser.parse_args()

if not parsed.f:
    print("[-]you must specify a file to be parsed\nuse --help for more info")
    sys.exit(1)

if not parsed.d:
    print("[-]you must specify a domain\nuse --help for more info")
    sys.exit(1)

if not parsed.u and not parsed.c and not parsed.g: #TODO add additional filetypes
    print("[-]you must specify the type of file that is being parsed\nuse --help for more info")
    sys.exit(1)

def tsvtodic(filename):
    fh = open(filename,'r')
    results = fh.read()
    fh.close()
    data = list(csv.DictReader(StringIO.StringIO(results), delimiter='\t'))
    return data

def parseUsers(filename,domain):
    domain = domain.upper()
    users = tsvtodic(filename)
    jsonUserData = {"users":[]}
    validCount = 0
    for item in users:
            validCount += 1
            jsonUserData["users"].append(
            {
                      "Properties": {
                        "domain": domain,
                        "objectsid": None,
                        "highvalue": False,
                        "enabled": True,
                        "lastlogon": None,
                        "lastlogontimestamp": None,
                        "pwdlastset": None,
                        "serviceprincipalnames": [],
                        "hasspn": False,#TODO fix this in the ad-ldap-enum script
                        "displayname": item["Display Name"].upper(),
                        "email": item["Email"].upper(),
                        "title": None,
                        "homedirectory": None,
                        "description": item["Description"],
                        "userpassword": None,
                        "sensitive": False,
                        "dontreqpreauth": False,
                        "admincount": True
                      },
                      "Name": item["SAM Account Name"].upper()+"@"+domain,
                      "PrimaryGroup": "DOMAIN USERS@"+domain,
                      "Aces": [],
                      "AllowedToDelegate": []
            }

    )

    metastring = "\"meta\":{\"type\":\"users\",\"count\":%d}" % (int(validCount))
    print "Meta string:",metastring
    userFileName = domain+'.users.json' 
    with open(userFileName, 'w') as fp:
        json.dump(jsonUserData, fp)

    #Work around for bloodhound's 'unique' json parsing problem:
    #https://github.com/BloodHoundAD/BloodHound/issues/254

    with open(userFileName, 'r') as _file :
            filedata = _file.read()

    filedata = filedata.replace('}]}', '}],%s}') % (metastring)

    with open(userFileName, 'w') as _file:
            _file.write(filedata)

    print ("User file written to {}".format(userFileName))

def parseComputers(filename,domain):
    domain = domain.upper()
    comps = tsvtodic(filename)
    validCount = 0
    jsonData = {"computers":[]}
    for item in comps:
            jsonData["computers"].append(
                {
                  "Properties": {
                        "haslaps": False,
                        "objectsid": None,
                        "highvalue": False,
                        "domain": domain 
                  },
                  "Name": item["SAM Account"].replace("$",'').upper()+"."+domain, 
                  "PrimaryGroup": None,
                  "LocalAdmins": [],
                  "RemoteDesktopUsers": [],
                  "DcomUsers": [],
                  "AllowedToDelegate": None,
                  "AllowedToAct": None,
                  "Aces": None
                }
            )
            validCount += 1

    #adding meta data and writing json file
    jsonData["meta"]={"count":validCount,"type":"computers"}

    with open(domain+'.computers.json', 'w') as fp:
        json.dump(jsonData, fp)
    print ("Computer file written to {}.computers.json".format(domain))


def aggregateGroups(roster,domain):
    retgroups = {}
    keys = roster[0].keys()
    i = 0
    total = len(roster)
    for line in roster:
        i+=1
        if line['Group Name'] not in retgroups.keys():
            retgroups[line['Group Name']] = {
                'users':[],
                'description':'none'
                    }
            if 'description' in line.keys():
                retgroups[line['Group Name']] = line['description']
        else:
            user = line['SAM Account Name'] + "@" + domain
            if user not in retgroups[line['Group Name']]['users']:
                retgroups[line['Group Name']]['users'].append({
                    "MemberName":user.upper(),
                    "MemberType":"user"
                    })
        print("progress: {}/{} users".format(i,total))
    return retgroups
            

def parseGroups(filename,domain):
    domain = domain.upper()
    groupdata_raw = tsvtodic(filename)
    groups = aggregateGroups(groupdata_raw,domain)
    jsonGroupData = {"groups":[]}
    validCount = 0
    for item in groups.keys():
            validCount += 1
            jsonGroupData["groups"].append(
            {
                    "Name": item.upper()+"@"+domain,
                    "Properties": {
                            "highvalue": False,
                            "domain": domain,
                            "objectsid": None,
                            "admincount": None, #TODO get this 
                            "description": groups[item]["description"]#TODO add this to the parser
                    },
                    "Aces": [],
                    "Members": groups[item]['users']
            }
    )

    groupFileName = domain+'.groups.json' 

    with open(groupFileName, 'w') as fp:
        json.dump(jsonGroupData, fp)


    metastring = "\"meta\":{\"type\":\"groups\",\"count\":%d}" % (int(len(groups.keys())))
    print "Meta string:",metastring
    #Work around for bloodhound's json parsing prob:
    #https://github.com/BloodHoundAD/BloodHound/issues/254

    with open(groupFileName, 'r') as _file :
            filedata = _file.read()

    filedata = filedata.replace('}]}', '}],%s}') % (metastring)

    with open(groupFileName, 'w') as _file:
            _file.write(filedata)

    print ("group file written to {}".format(groupFileName))


if parsed.u:
    print("parsing users")
    try:
        parseUsers(parsed.f,parsed.d)
        sys.exit(0)
    except Exception as e:
        print("[-]failed to parse users:\n",e)
        sys.exit(1)

if parsed.c:
    print("parsing computers")
    try:
        parseComputers(parsed.f,parsed.d)
        sys.exit(0)
    except Exception as e:
        print("[-]failed to parse computers:\n",e)
        sys.exit(1)

if parsed.g:
    print("parsing groups")
    try:
        parseGroups(parsed.f,parsed.d)
        sys.exit(0)
    except Exception as e:
        print("[-]failed to parse groups:\n",e)
        sys.exit(1)

