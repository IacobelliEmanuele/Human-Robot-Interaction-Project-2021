import os
import sys
import time
import threading as t
import cv2
import Queue
import json

from websocket import create_connection

def msg(d1,d2):
    return '{ "type": "'+str(d1)+'", "value": "'+str(d2)+'" }'

def ser_listening(q):
    while True: 
        q.put(ws.recv())

def ask(q):
    while True:
        r = ''
        while r == '':
            r = pepper_cmd.robot.asr(vocabulary,timeout)
        s = '{ "type": "'+str(r)+'", "value": "" }'
        q.put(s) 

def wait_ris():
    global t3,t4,q
    blueEyes()
    m = q.get(True)
    while not q.empty():
        try:
            q.get(False)
        except Empty:
            continue
    ris = json.loads(m)
    return ris['type']

def init():

    f = open("IngrRecipes.txt",'r')
    r = f.read()
    r = r.replace("\n", "").split('%')
    r.pop(len(r)-1)
    for i in r:
        data = i.split("$")
        ingr = data[0]
        recipes = data[1].split("/")
        l = []
        for j in recipes:
            data1 = j.split("@")
            n_v = data1[0].split(" ")
            l.append(n_v[0]) 
            dicGrad[n_v[0]] = n_v[1]
            dicRecipes[n_v[0]] = data1[1]
        dicIngr[ingr] = l
    global ingredients
    ingredients = dicIngr.keys()
    f.close()

    f = open("CuisRecipes.txt",'r')
    r = f.read()
    r = r.replace("\n", "").split('%')
    r.pop(len(r)-1)
    for i in r:
        data = i.split("$")
        cuis = data[0]
        recipes = data[1].split("/")
        l = []
        for j in recipes:
            data1 = j.split("@")
            n_v = data1[0].split(" ")
            l.append(n_v[0]) 
            dicGradCuis[n_v[0]] = n_v[1]
            dicRecipesCuis[n_v[0]] = data1[1]
        dicCuis[cuis] = l
    global cuisines
    cuisines = dicCuis.keys()
    f.close()

def blueEyes():
    global img
    pepper_cmd.robot.blue_eyes() 
    img = cv2.imread("LedsBlue.jpg")
    cv2.imshow("Pepper",img)
    cv2.waitKey(1)

def greenEyes():
    global img
    pepper_cmd.robot.green_eyes()
    img = cv2.imread("LedsGreen.jpg")
    cv2.imshow("Pepper",img)
    cv2.waitKey(1)

def talk(string, mood):
    greenEyes()
    pepper_cmd.robot.say(string)
    #pepper_cmd.robot.anspeech_service.say("^startTag("+mood+") " + string + " ^waitTag("+mood+")")
    

img = None
ext = False
kitchen = False
Touch = False
change = False
menu = False

ingredients = []
dicIngr = {}
dicGrad = {}
dicRecipes = {}

cuisines = []
dicCuis = {}
dicGradCuis = {}
dicRecipesCuis = {}

currentRec=None

vocabulary = ['yes','no']
timeout = 60

movLock = t.Lock()
movSem = t.Semaphore(1)

# Function that will move the robot in the kitchen 
def fake_move():
    greenEyes()
    pepper_cmd.forward(1)
    greenEyes()
    pepper_cmd.right(1)
    greenEyes()
    pepper_cmd.forward(1)
    greenEyes()
    pepper_cmd.left(1)

def chooseRecipe(obj, dic, dic1, dic2, s):
    global change, menu
    while True:
        back = False
        
        str1 = "You've chosen "+obj+". The avaiable recipes are: "

        def takeSecond(elem):
            return elem[1]

        l = []
        for i in dic1[obj]:
            l.append( (i, dic[i] ) )
        
        l.sort(key=takeSecond,reverse=True)

        for i in l:
            str1+= " "+i[0]
        str1 += ". Tell me the recipe you want to prepare."
        
        talk(str1,'explain')
        
        ans = wait_ris()

        if ans in dic1[obj]:

            ws.send(msg('recipe', ans))

            global currentRec
            currentRec = ans

            str1 = "You've chosen "+ans+"."
            talk(str1,"explain")
            str1 = "I'll read you the recipe step by step and at the end of the phrase you can:"
            talk(str1,"explain")
            str1 = "Tell me 'repeat' if you want to listen again the last step;"
            talk(str1,"explain")
            str1 = "Tell me 'restart' if you want to listen the recipe from the beginning;"  
            talk(str1,"explain")
            str1 = "Tell me 'stop' and I'll wait until you say 'resume' for continuing the reading of the recipe;"
            talk(str1,"explain")
            str1 = "Tell me 'continue' and I'll continue reading the recipe." 
            talk(str1,"explain")
            str1 = "Let's cook!"
            talk(str1,"excited")

            phrases = dic2[ans].split(".")
            j = 0
            while j != len(phrases):
                
                talk(phrases[j], "explain")

                ans = wait_ris()
                
                if ans == "repeat":
                    talk(phrases[j],"explain")
                    time.sleep(2)
                elif ans == "restart":
                    greenEyes()
                    j = -1
                    time.sleep(2)
                elif ans == "back":
                    greenEyes()
                    ws.send(msg('utils', ans))
                    back = True
                    break
                elif ans == "continue":
                    j+= 1
                    continue
                elif ans == "stop":
                    talk("I'm waiting until you say 'resume.'", "explain")
                    while True:
                        ans = wait_ris()
                        if ans == "resume":
                            break
                elif ans=="stop cooking":
                    ws.send(msg(ans, ''))
                    talk("We'll cook another time!","hello")
                    return False
                elif ans == "change "+s:
                    ws.send(msg('utils', ans))
                    change = True
                    return False
                elif ans == "menu":
                    ws.send(msg('utils', ans))
                    menu = True
                    return False
                j+=1
            if not back:
                break
        elif ans == "change "+s:
            ws.send(msg('utils', ans))
            change = True
            return False
        elif ans=="stop cooking":
            ws.send(msg(ans, ''))
            talk("We'll cook another time!","hello")
            return False
        elif ans=="menu":
            ws.send(msg('utils', ans))
            menu = True
            return False
        else:
            str1 = "You've chosen "+ans+". This recipe isn't avaiable, choose another one."
            talk(str1, "sad")
    return True

def chooseObj(lst, dic, dic1, dic2, s):
    global change, menu
    while True:    
        change = False
        str1 = "You've chosen "+s+". Choose one between the avaiable ones or tell me 'menu' to return to the choice between ingredient and world cuisine. "
        str1 += "The avaiable "+s+" ones are:"
        for i in lst:
            str1 += " "+i
        talk(str1, "explain")                  

        ans = wait_ris()

        if ans in lst:
            ws.send(msg(s, ans))
            if chooseRecipe(ans, dic, dic1, dic2, s):
                break
            elif not change:
                return False
        elif ans == "menu":
            menu = True
            ws.send(msg('utils', 'menu'))
            return False
        elif ans=="stop cooking":
            ws.send(msg(ans, ''))
            talk("We'll cook another time!","hello")
            return False
        else:
            ws.send(msg(s, ans))
            str1 = "You've chosen "+ans+". There aren't avaiable recipes for this "+s+", choose another one."
            talk(str1,"sad")

    return True

def writing(s, dic, ans):
    global currentRec
    f = open(s, "r+")
    data = f.read()
    try: 
        ris = data.replace(currentRec + " " + dic[currentRec], currentRec + " " + ans)
        f.seek(0)
        f.write(ris)
        f.truncate()
        dic[currentRec] = ans
    except:
        pass
    f.close()


def giveValutation():

    global currentRec

    talk("The recipe is finished!","explain")

    while True:
        
        greenEyes()
        ws.send(msg('vote', ''))
        str1 = "How much do you like this recipe from 1 to 5?"
        talk(str1, "explain")

        ans = wait_ris()
        l = ['1','2','3','4','5']
        
        if ans in l:
            ws.send(msg('vote', ans))
            str1 = "You've votated: "+ans+". I wish you a good meal!"
            talk(str1, "excited")
            writing("IngrRecipes.txt", dicGrad, ans)
            writing("CuisRecipes.txt", dicGradCuis, ans)
            ws.send(msg('stop cooking', ''))
            break
        elif ans=="stop cooking":
            ws.send(msg(ans, ''))
            talk(" I wish you a good meal! ","hello")
            break

def listening():
    while True:

        global movLock, kitchen, menu
            
        if ext:
            return

        answer = wait_ris()

        if answer == "hey pepper, follow me in the kitchen":
            
            movSem.acquire()
            movLock.acquire()

            if not kitchen:
                str1 = "I'm coming!"
                talk(str1, "affirmative")
                fake_move()  
                str1 = "I'm here!"
                talk(str1,"excited")
                kitchen = True
            else:
                str1 = "I'm already in the kitchen."
                talk(str1,"calm")
                
            movLock.release()
            movSem.release()

        elif answer == "let's cook":
            
            ws.send(msg(answer, ''))

            while True:

                menu = False

                greenEyes()
                str1 = "Okay I'm ready. Tell me if you want to prepare a recipe starting from an ingredient or a world cuisine."
                str2 = "You can also choose it on the tablet."
                talk(str1,"explain")
                talk(str2,"tablet")

                ans = wait_ris()
                
                if ans=="ingredient":

                    ws.send(msg(ans, ''))

                    if chooseObj(ingredients, dicGrad ,dicIngr, dicRecipes,"ingredient"):
                        giveValutation()
                        break
                    elif not menu:
                        break

                elif ans=="world cuisine":

                    ws.send(msg(ans, ''))
                    if chooseObj(cuisines, dicGradCuis, dicCuis, dicRecipesCuis, "world cuisine"):
                        giveValutation()
                        break
                    elif not menu:
                        break

                elif ans=="stop cooking":

                    ws.send(msg(ans, ''))
                    talk("We'll cook another time!","hello")
                    break

                else:
                    greenEyes()
                    str1 = "I don't understood, please repeat if you want to prepare a recipe starting from an ingredient or a world cuisine."
                    talk(str1,"unknown")
                
        elif answer != "":
            print("--------------", answer)
            talk("I don't understood, please repeat the sentence!","cogitate")
        
        time.sleep(1)

def touching():
    while True:

        global movLock, kitchen, Touch

        if ext:
            return
        
        headTouch = pepper_cmd.robot.sensorvalue('headtouch')
        if headTouch == 0.0:
            Touch = False

        if headTouch and not Touch:

            movSem.acquire()
            movLock.acquire()

            if not kitchen:
                talk("I'm coming!","excited")
                fake_move() 
                talk("I'm here!","excited")
                blueEyes()
                kitchen = True
            else:
                talk("I'm already in the kitchen.","excited")
                blueEyes()

            movLock.release()
            movSem.release()

            Touch = True

        time.sleep(1)

ws = create_connection("ws://localhost:3000/ws")

pdir = os.getenv('PEPPER_TOOLS_HOME')
sys.path.append(pdir+'/cmd_server')
sys.path.append(pdir+'/cmd_server')
import pepper_cmd
from pepper_cmd import *

begin()

pepper_cmd.robot.startSensorMonitor()

img = cv2.imread("LedsOff.jpeg")
cv2.imshow("Pepper",img)
cv2.waitKey(2000)

talk("Hi, I'm Pepper. I'm ready to listen you!", "excited")
blueEyes()

init()

t1 = t.Thread(target=listening)
t2 = t.Thread(target=touching)


q = Queue.LifoQueue()
t3 = t.Thread(target=ask, args=[q])
t4 = t.Thread(target=ser_listening, args=[q])
t3.start()
t4.start()

t1.start()
t2.start()

p = ""
while p!= "e":
    p = raw_input("-----Press e to terminate the program-----\n")    

ext = True

pepper_cmd.robot.stopSensorMonitor()

cv2.destroyAllWindows()
ws.close()
end()
