# -*- coding:utf-8 -*-

Debug = 2
TriggerOnSpeed = 35
TriggerOffSpeed = 25


RedLedPin = 3
GreenLedPin = 4
ActivityLedPin = 5

import time
import l76x
import math
import ePaper
from machine import Pin
import ujson
import _thread
import gc

LedFlashOn = 0.7
LedFlashOff = 0.3
TSDataFile = "TugTimesData.json"
DebugDataFile = "DebugDataFile.txt"
TSHistory = 7
RawData = []
LM = ""
LMC = 0

EPD_WIDTH       = 104
EPD_HEIGHT      = 212
# 13 characters wide
# 14 10 pixel lines height

# GPS Status LED(s)
GpsLedRed = Pin(RedLedPin, Pin.OUT)
GpsLedGreen = Pin(GreenLedPin, Pin.OUT)

def GetGps():
    x.Status = 0
    while (x.Status != 1):
        sleep(1)
        x.L76X_Gat_GNRMC()
        
    return

def Log(Message):
    global Debug, LM, LMC
    if (Debug < 1):
        return
    
    if (Message == LM):
        LMC = LMC + 1
        return
    
    if (Debug == 1):
        print(f"{LMC}:{Message}")
    else:
        try:
            dfh = open(DebugDataFile, mode='a+t', encoding='utf-8')
            dfh.write(f"{LMC}:{Message}\n")
            dfh.close()
        except:
            Debug = 0
          
    LM = Message
    LMC = 0
    return
        

def PaintScreen(epd, RawData):
    Log("PaintScreen")
    epd.imageblack.fill(0xff)
    epd.imagered.fill(0xff)

    epd.imageblack.text("Tug Times 1.0", 1, 3, 0x00)
    p = 0
    for line in range(20, 186, 26):
        LDT = time.gmtime(RawData[p][0])
        FTT = time.gmtime(RawData[p][1])
        epd.imageblack.text("{0:2d}/{1:02d}/{2:4d}".format(LDT[2], LDT[1], LDT[0]), 12, line, 0x00)
        epd.imageblack.text("{0:2d}:{1:02d}".format(FTT[3], FTT[4]), 20, line + 13, 0x00)
        epd.imageblack.text("{0:2d}L".format(RawData[p][2]), 70, line + 13, 0x00)
        epd.imageblack.vline(7, line - 2, 26, 0x00)
        epd.imageblack.vline(97, line - 2, 26, 0x00)
        epd.imageblack.hline(7, line - 3, 91, 0x00)
        p = p + 1
        
    epd.imageblack.hline(7, line + 23, 91, 0x00)
    epd.display()
    return

def DriveLed(Colour, Action):
    if (Action == "on"):
        if (Colour == "red"):
            GpsLedRed.on()
            GpsLedGreen.off()
        elif (Colour == "green"):
            GpsLedGreen.on()
            GpsLedRed.off()
        else:
            GpsLedRed.on()
            GpsLedGreen.on()
            
    elif (Action == "off"):
        if (Colour == "red"):
            GpsLedRed.off()
        elif (Colour == "green"):
            GpsLedGreen.off()
        else:
            GpsLedRed.off()
            GpsLedGreen.off()
            
    elif (Action == "flash"):
        if (Colour == "red"):
            GpsLedRed.off()
            GpsLedGreen.off()
            time.sleep(LedFlashOff)
            GpsLedRed.on()
            time.sleep(LedFlashOn)
        elif (Colour == "green"):
            GpsLedGreen.off()
            GpsLedRed.off()
            time.sleep(LedFlashOff)
            GpsLedGreen.on()
            time.sleep(LedFlashOn)
        else:
            GpsLedRed.off()
            GpsLedGreen.off()
            time.sleep(LedFlashOff)
            GpsLedRed.on()
            GpsLedGreen.on()
            time.sleep(LedFlashOn)

    return
        

Log("\nPowerOn")
DriveLed("red", "on")

# Fire up the eInk display
epd = ePaper.EPD_2in13_B()
        
# Fire up the GPS
x=l76x.L76X()
x.L76X_Set_Baudrate(9600)
x.L76X_Send_Command(x.SET_NMEA_BAUDRATE_115200)
time.sleep(2)
x.L76X_Set_Baudrate(115200)
x.L76X_Send_Command(x.SET_POS_FIX_400MS);
#Set output message
x.L76X_Send_Command(x.SET_NMEA_OUTPUT);
time.sleep(2)
x.L76X_Exit_BackupMode();
x.L76X_Send_Command(x.SET_SYNC_PPS_NMEA_ON)

# Load Datafile and print the screen
try:
    fh = open(TSDataFile, mode='r+t', encoding='utf-8')
    RawData = ujson.load(fh)
    fh.close()
except: 
   Log("ReadFileErr")
  
if (len(RawData) != TSHistory):
    Log("BadDataFileRecreate")
    del RawData  # Delete and recreate the list
    RawData = [[0] * 3] * TSHistory

PaintScreen(epd, RawData)

# Wait for valid GPS
while (1):
    while(1):
        x.L76X_Gat_GNRMC()
        if(x.Status == 1):
            Log('GpsLock')
            if (x.Date < 21221):  # Good date if its greater then 02/12/21
                Log(f"BadDate:{x.Date}")
            else:
                break
        Log(f"NGL1:{x.Status}")
        DriveLed("red", "flash")
        DriveLed("red", "flash")

    DriveLed("green", "on")
    Log(f"WTOS:{x.Time_H}:{x.Time_M}:{x.Time_S}UTC Mem:{gc.mem_free()}")
    while (x.Status != 1 or x.Speed < TriggerOnSpeed):
        if(x.Status != 1):
            Log(f"NGL2:{x.Status}")
            DriveLed("red", "flash")
            DriveLed("red", "flash")
        else:
            DriveLed("green", "on")
            time.sleep(1.75)
            DriveLed("green", "off")
            time.sleep(0.25)
            DriveLed("green", "on")
            
        x.L76X_Gat_GNRMC()

    # We are at TO speed.
    # Record Start Time (And add in 8 hours for WA TZ)
    LocalStartUnix = time.mktime(eval("x.Date_Y, x.Date_M, x.Date_D, x.Time_H, x.Time_M, x.Time_S, 0, 0")) + 28800
    LocalDateUnix = time.mktime(eval("x.Date_Y, x.Date_M, x.Date_D, 0, 0, 0, 0, 0")) + 28800
    LSTT = time.gmtime(LocalStartUnix)
    LDT = time.gmtime(LocalDateUnix)
    Log(f"TO:{LDT[2]}/{LDT[1]}/{LDT[0]} {LSTT[3]}:{LSTT[4]}:{LSTT[5]}")
  
    # We now wait until we have slowed down
    while (x.Status != 1 or x.Speed > TriggerOffSpeed):
        if(x.Status != 1):
            Log(f"NGL3:{x.Status}")
            DriveLed("red", "flash")
            DriveLed("red", "flash")
        else:
            DriveLed("yellow", "on")
            time.sleep(2)
            
        x.L76X_Gat_GNRMC()
        if (x.Status == 1):
            LocalEndUnix = time.mktime(eval("x.Date_Y, x.Date_M, x.Date_D, x.Time_H, x.Time_M, x.Time_S, 0, 0")) + 28800
            if (LocalEndUnix < LocalStartUnix or LocalEndUnix > (LocalStartUnix + 36000)):
                # We have a bad timestamp, less than start or more than 10 hours.
                Log(f"BadTimeStamp:{LocalStartUnix}:{LocalEndUnix}")
                x.Status = -10

    # Now that we have a cycle.
    DriveLed("green", "on")
    LETT = time.gmtime(LocalEndUnix)
    Log(f"Landed:{LETT[3]}:{LETT[4]}:{LETT[5]}")
    
    FlightTime = int(LocalEndUnix - LocalStartUnix)
    if (FlightTime < 1 or FlightTime > 14400 or x.Status != 1):
        FlightTime = 0
    Log(f"FT:{FlightTime}")

        
    if (FlightTime > 0):
        # work out if the last date is todays date
        if (LocalDateUnix != RawData[TSHistory - 1][0]):
            Log("NewEntryInLog.")
            del RawData[0]
            RawData.append([0, 0, 0])
        
        # Work out the total time for the day and update the matrix 
        FileFlightTime = RawData[TSHistory - 1][1] + FlightTime
        FileLandings = RawData[TSHistory - 1][2] + 1

        RawData[TSHistory - 1][0] = LocalDateUnix
        RawData[TSHistory - 1][1] = FileFlightTime
        RawData[TSHistory - 1][2] = FileLandings
        
        try:
            fh = open(TSDataFile, mode='w+t', encoding='utf-8')
            ujson.dump(RawData, fh)
            fh.close()
        except:
            Log("FileWriteError")
            
        PaintScreen(epd, RawData)
        Log(f"NextCycle. Mem:{gc.mem_free()}")
        time.sleep(2)
    else:
        # Wait for things to flush
        Log("BadProgramFlow. ***EntryNotRecorded** Status:{x.Status}")
        p = 0
        while (p < 10):
            DriveLed("yellow", "flash")
            p = p + 1
        DriveLed("green", "on")

# End of program