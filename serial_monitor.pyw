import tkinter as tk
from tkinter import ttk as ttk
from tkinter import scrolledtext as tkscroll
from tkinter import messagebox as msgbox
import serial
import serial.tools.list_ports as list_ports
import time
import json
import crcmod
import sys

#Constants
header = "1002"
end = "1003"
#---------- INICIALIZACION ----------
MSG2000 = "100232303030303033353030323530303630323032333035323631313334313630403030301003" #Inicialización
#---------- ESTADO REPOSO -----------
MSG2001 = "1002323030313030313630303031403030301003" #200100160001@000
#---------- OPERATIVA BANDA ---------
MSG1001 = "1002313030313030323830303032303030303031303135303038403030301003" #100100280002000001015008@000
MSG0310 = "10023033313030303136303030334030343435463238434F4D50524F42414E444F204445534355454E544F535C6E45535045524520504F52204641564F521003" #App confirma lectura 031000600003@0445F28COMPROBANDO DESCUENTOS\nESPERE POR FAVOR (D2-1A)
MSG1000 = "100231303030303032363030303030313031353030383032403030301003" #Inicia transaccion 1000002600000101500802@000
MSG0020 = "1002303032303030353130303031254441544F5320412050414E54414C4C41254441544F53204120494D505245534F5241403030301003" #Verifica mensaje 002000510001%DATOS A PANTALLA%DATOS A IMPRESORA@000
#---------- OPERATIVA EMV -----------
#Ini: 100100280002000001015008@000
MSG1001 = "1002313030313030323830303032303030303031303135303038403030301003"
#App confirma lectura: 031000600003@0445F28COMPROBANDO DESCUENTOS\nESPERE POR FAVOR
MSG0310 = "10023033313030303630303030334030343435463238434F4D50524F42414E444F204445534355454E544F535C6E45535045524520504F52204641564F521003" 
#Inicia transaccion: 1000002600000101500802@000
MSG1000 = "100231303030303032363030303030313031353030383032403030301003" 
#Pantalla DCC: 1002009904USD 0644441544F532041205649534F5220504152412050414E54414C4C415320444343%DATOS A IMPRESORA
MSG1002 = "1002313030323030393930345553442030363434343431353434463533323034313230353634393533344635323230353034313532343132303530343134453534343134433443343135333230343434333433254441544F53204120494D505245534F52411003" 
#Respuesta autorizacion: 0110011100088A0230300000%4441544F532041205649534F5220504152412050414E54414C4C415320444343%DATOS A IMPRESORA@000
MSG0110 = "10023031313030313131303030383841303233303330303030302534343431353434463533323034313230353634393533344635323230353034313532343132303530343134453534343134433443343135333230343434333433254441544F53204120494D505245534F5241403030301003" 
#Finaliza transacción: ERROR - 011100160000@000; SIN FIRMA - 011100160001@000; FIRMA RECIBIDA - 011100160002@000
MSG0111 = "1002303131313030313630303032403030301003"

rx = ''
#-------------------------------------------------- CRC --------------------------------------------------
def calc_crc(text):
	_CRC_FUNC = crcmod.mkCrcFun(0x11021, rev=False, initCrc=0x0000, xorOut=0x0000)
	data = bytearray.fromhex(text)
	crc = _CRC_FUNC(data)
	return crc

def append_crc(text):
	textCRC = text.removeprefix(header)
	crc = calc_crc(textCRC)
	crc_str = hex(crc).removeprefix("0x")
	return text.__add__(crc_str)

#-------------------------------------------------- CHR/STR/HEX --------------------------------------------------
def get_str_of_chr(chr_in_byte):
	cd = ord(chr_in_byte)
	if 0x20 <= cd and cd <= 0x7e or 0xa1 <= cd:
		if cd == 92:
			return '\\\\'
		return chr(cd)
	else:
		if cd == 9:
			return '\t'
		elif cd == 10:
			return '\n'
		elif cd == 13:
			return '\\r'
	return '\\x{:02x}'.format(cd)

def get_hexstr_of_chr(chr_in_byte):
	cd = ord(chr_in_byte)
	st = '{:02X}'.format(cd)
	if cd == 10:
		st += '\n'
	else:
		st += ' '
	return st

#-------------------------------------------------- CMD --------------------------------------------------
def upKeyCmd(event):
	global sentTextsPtr, lastTxText
	if sentTextsPtr == len(sentTexts):
		lastTxText = str(txText.get())
	if sentTextsPtr > 0:
		sentTextsPtr -= 1
		txText.delete(0, tk.END)
		txText.insert(tk.END, sentTexts[sentTextsPtr])

def downKeyCmd(event):
	global sentTextsPtr
	if sentTextsPtr < len(sentTexts):
		sentTextsPtr += 1
		txText.delete(0, tk.END)
		if sentTextsPtr == len(sentTexts):
			txText.insert(tk.END, lastTxText)
		else:
			txText.insert(tk.END, sentTexts[sentTextsPtr])

def clearOutputCmd():
	global isEndByNL, lastUpdatedBy
	rxText.configure(state=tk.NORMAL)
	rxText.delete('1.0', tk.END)
	rxText.configure(state=tk.DISABLED)
	isEndByNL = True
	lastUpdatedBy = 2

def sendCmd(event):
	global sentTexts, sentTextsPtr, rx
	rx = ''
	txt = str(txText.get())
	lst = len(sentTexts)
	if txt != '':
		txt = append_crc(txt)
		bs = bytes.fromhex(txt)
		print("bs",bs)
		if lst > 0 and sentTexts[lst-1] != txt or lst == 0:
			sentTexts.append(txt)
		sentTextsPtr = len(sentTexts)
		if lineEndingCbo.current() == 1:
			bs += b'\n'
		elif lineEndingCbo.current() == 2:
			bs += b'\r'
		elif lineEndingCbo.current() == 3:
			bs += b'\r\n'
		currentPort.write(bs)
		if showSentTextVar.get():
			if dispHexVar.get():
				txt = ''.join([get_hexstr_of_chr(bytes([i])) for i in bs])
			else:
				txt = ''.join([get_str_of_chr(bytes([i])) for i in bs])
			writeConsole(txt, 1)
		txText.delete(0, tk.END)

def sendMSG2000Cmd(event):
	sendMSGCmd(MSG2000)

def sendMSG2001Cmd(event):
	sendMSGCmd(MSG2001)

def sendOPEMVCmd(event):
	sendMSGCmd(MSG1001)

def sendMSGCmd(MSG):
	global rx
	rx = ''
	txt = MSG
	txt = append_crc(txt)
	bs = bytes.fromhex(txt)
	if lineEndingCbo.current() == 1:
		bs += b'\n'
	elif lineEndingCbo.current() == 2:
		bs += b'\r'
	elif lineEndingCbo.current() == 3:
		bs += b'\r\n'
	currentPort.write(bs)
	if showSentTextVar.get():
		if dispHexVar.get():
			txt = ''.join([get_hexstr_of_chr(bytes([i])) for i in bs])
		else:
			txt = ''.join([get_str_of_chr(bytes([i])) for i in bs])
		writeConsole(txt, 1)

#-------------------------------------------------- PORT --------------------------------------------------
def changePort(event):
	global portDesc
	if portCbo.get() == currentPort.port:
		return
	disableSending()
	if currentPort.is_open:
		currentPort.close()
		writeConsole(portDesc + ' closed.\n', 2)
	currentPort.port = portCbo.get()
	portDesc = ports[currentPort.port]
	writeConsole('Opening ' + portDesc + '...', 2)
	root.update()
	try:
		currentPort.open()
	except:
		root.title(APP_TITLE)
		portCbo.set('Select port')
		#msgbox.showerror(APP_TITLE, "Couldn't open the {} port.".format(portDesc))
		writeConsole('failed!!!\n', 2)
		currentPort.port = None
	if currentPort.is_open:
		root.title(APP_TITLE + ': ' + ports[currentPort.port])
		enableSending()
		rxPolling()
		writeConsole('done.\n', 2)
		#msgbox.showinfo(APP_TITLE, '{} opened.'.format(portDesc))

def changeBaudrate(event):
	currentPort.baudrate = BAUD_RATES[baudrateCbo.current()]

def rxPolling():
	global rx
	if not currentPort.is_open:
		return
	preset = time.perf_counter_ns()
	try:	
		while currentPort.in_waiting > 0 and time.perf_counter_ns()-preset < 2000000: # loop duration about 2ms
			ch = currentPort.read()
			tm = time.strftime('%H:%M:%S.{}'.format(repr(time.time()).split('.')[1][:3]))
			txt = ''
			if dispHexVar.get():
				txt += get_hexstr_of_chr(ch)
			else:
				txt += get_str_of_chr(ch)
			writeConsole(txt)
			# print("rxPolling ",txt)
			rx += txt
	except serial.SerialException as se:
		closePort()
		msgbox.showerror(APP_TITLE, "Couldn't access the {} port".format(portDesc))
	checkReceiveMSG()
	root.after(5, rxPolling) # polling in 10ms interval

def checkReceiveMSG():
	global rx
	rx = rx.replace(" ","")
	if rx.rfind(header) < 0 or rx.rfind(end) < 0 or len(rx) != rx.rfind(end)+8:
		return
	len_rx =len(rx)
	print("--------------RX: ",rx, len_rx, rx.rfind(end))
	rx_msg = bytes.fromhex(rx)[2:6]
	msg = bytes.decode(rx_msg,'utf-8')
	match msg:
		case "0300":
			print("MSG: 0300")
			sendMSGCmd(MSG0310)
			sendMSGCmd(MSG1000)
		case "0101":
			print("MSG: 0101")
			sendMSGCmd(MSG0111)
		case "0100":
			print("MSG: 0100")
			sendMSGCmd(MSG0110)
	rx = ''

def listPortsPolling():
	global ports
	ps = {p.name: p.description for p in list_ports.comports()}
	pn = sorted(ps)
	if pn != portCbo['values']:
		portCbo['values'] = pn
		if len(ports) == 0: # if no port before
			portCbo['state'] = 'readonly'
			portCbo.set('Select port')
			enableSending()
		elif len(pn) == 0: # now if no port
			portCbo['state'] = tk.DISABLED
			portCbo.set('No port')
			disableSending()
		ports = ps
	root.after(1000, listPortsPolling) # polling every 1 second

def closePort():
	if currentPort.is_open:
		currentPort.close()
		writeConsole(portDesc + ' closed.\n', 2)
		currentPort.port = None
		disableSending()
		portCbo.set('Select port')
		root.title(APP_TITLE)

#-------------------------------------------------- MENU --------------------------------------------------
def showTxTextMenu(event):
	if txText.selection_present():
		sta=tk.NORMAL
	else:
		sta=tk.DISABLED
	for i in range(2):
		txTextMenu.entryconfigure(i, state=sta)
	try:
		root.clipboard_get()
		txTextMenu.entryconfigure(2, state=tk.NORMAL)
	except:
		txTextMenu.entryconfigure(2, state=tk.DISABLED)
	try:
		txTextMenu.tk_popup(event.x_root, event.y_root)
	finally:
		txTextMenu.grab_release()

def showRxTextMenu(event):
	if len(rxText.tag_ranges(tk.SEL)):
		rxTextMenu.entryconfigure(0, state=tk.NORMAL)
	else:
		rxTextMenu.entryconfigure(0, state=tk.DISABLED)
	if currentPort.isOpen():
		rxTextMenu.entryconfigure(2, state=tk.NORMAL)
	else:
		rxTextMenu.entryconfigure(2, state=tk.DISABLED)
	try:
		rxTextMenu.tk_popup(event.x_root, event.y_root)
	finally:
		rxTextMenu.grab_release()

#-------------------------------------------------- WRITE --------------------------------------------------
def writeConsole(txt, upd=0):
	global isEndByNL, lastUpdatedBy
	tm = ''
	ad = ''
	if upd != 2 and showTimestampVar.get():
		tm = time.strftime('%H:%M:%S.{}'.format(repr(time.time()).split('.')[1][:3]))
	if not upd:
		if not lastUpdatedBy and isEndByNL or lastUpdatedBy:
			if showSentTextVar.get() and showTimestampVar.get():
				ad += 'RX_' + tm
			elif showSentTextVar.get():
				ad += 'RX'
			elif showTimestampVar.get():
				ad += tm
			if ad:
				ad += ' >> '
			if not isEndByNL:
				ad = '\n' + ad
	elif upd == 1:
		if lastUpdatedBy == 1 and isEndByNL or lastUpdatedBy != 1:
			if showTimestampVar.get():
				ad = 'TX_' + tm
			else:
				ad = 'TX'
			ad += ' >> '
			if not isEndByNL:
				ad = '\n' + ad
	elif upd == 2:
		if lastUpdatedBy != 2:
			ad = '\n'
			if not isEndByNL:
				ad += '\n'
	else:
		return
	if upd !=2 and lastUpdatedBy == 2:
		ad = '\n' + ad
	ad += txt
	rxText.configure(state=tk.NORMAL)
	rxText.insert(tk.END, ad)
	if autoscrollVar.get() or upd == 2:
		rxText.see(tk.END)
	rxText.configure(state=tk.DISABLED)
	if txt[-1] == '\n':
		isEndByNL = True
	else:
		isEndByNL = False
	lastUpdatedBy = upd


#-------------------------------------------------- SETTINGS --------------------------------------------------
def setting():
	global settingDlg, dataBitsCbo, parityCbo, stopBitsCbo
	settingDlg = tk.Toplevel()
	settingDlg.title('Port Setting')
	if ico:
		settingDlg.iconphoto(False, ico)
	tk.Grid.rowconfigure(settingDlg, 0, weight=1)
	tk.Grid.rowconfigure(settingDlg, 1, weight=1)
	tk.Grid.rowconfigure(settingDlg, 2, weight=1)
	tk.Grid.rowconfigure(settingDlg, 3, weight=1)
	tk.Grid.columnconfigure(settingDlg, 0, weight=1)
	tk.Grid.columnconfigure(settingDlg, 1, weight=1)
	tk.Grid.columnconfigure(settingDlg, 2, weight=1)
	tk.Label(settingDlg, text='Data bits:').grid(row=0, column=1, padx=0, pady=12, sticky=tk.NE)
	tk.Label(settingDlg, text='Parity:').grid(row=1, column=1, padx=0, pady=0, sticky=tk.NS+tk.E)
	tk.Label(settingDlg, text='Stop bits:').grid(row=2, column=1, padx=0, pady=12, sticky=tk.NE)
	dataBitsCbo = ttk.Combobox(settingDlg, width=10, state='readonly')
	dataBitsCbo.grid(row=0, column=2, padx=12, pady=12, sticky=tk.NE)
	dataBitsCbo['values'] = DATABITS
	dataBitsCbo.set(currentPort.bytesize)
	parityCbo = ttk.Combobox(settingDlg, width=10, state='readonly')
	parityCbo.grid(row=1, column=2, padx=12, pady=0, sticky=tk.NS+tk.E)
	parityCbo['values'] = PARITY_VAL
	parityCbo.current(PARITY.index(currentPort.parity))
	stopBitsCbo = ttk.Combobox(settingDlg, width=10, state='readonly')
	stopBitsCbo.grid(row=2, column=2, padx=12, pady=12, sticky=tk.NE)
	stopBitsCbo['values'] = STOPBITS
	stopBitsCbo.set(currentPort.stopbits)
	tk.Button(settingDlg, text='Default', width=10, command=defaultSetting).\
		grid(row=1, column=0, padx=12, pady=0, sticky=tk.NS+tk.W)
	tk.Button(settingDlg, text='OK', width=10, command=lambda:setPort(None)).\
		grid(row=3, column=1, padx=0, pady=12, sticky=tk.S)
	cancelBtn = tk.Button(settingDlg, text='Cancel', width=10, command=lambda:hideSetting(None))
	cancelBtn.grid(row=3, column=2, padx=12, pady=12, sticky=tk.S)
	settingDlg.bind('<Return>', setPort)
	settingDlg.bind('<Escape>', hideSetting)
	settingDlg.update()
	rw = root.winfo_width()
	rh = root.winfo_height()
	rx = root.winfo_rootx()
	ry = root.winfo_rooty()
	dw = settingDlg.winfo_width()
	dh = settingDlg.winfo_height()
	settingDlg.geometry(f'{dw}x{dh}+{rx+int((rw-dw)/2)}+{ry+int((rh-dh)/2)}')
	settingDlg.minsize(dw, dh)
	settingDlg.maxsize(dw, dh)
	settingDlg.resizable(0, 0)
	settingDlg.grab_set()
	cancelBtn.focus_set()

def defaultSetting():
	dataBitsCbo.set(serial.EIGHTBITS)
	parityCbo.current(PARITY.index(serial.PARITY_NONE))
	stopBitsCbo.set(serial.STOPBITS_ONE)

def setPort(event):
	currentPort.bytesize = DATABITS[dataBitsCbo.current()]
	currentPort.parity = PARITY[parityCbo.current()]
	currentPort.stopbits = STOPBITS[stopBitsCbo.current()]
	settingDlg.destroy()

def hideSetting(event):
	settingDlg.destroy()

def disableSending():
	sendBtn['state'] = tk.DISABLED
	txText.unbind('<Return>')
	MSG2000Btn['state'] = tk.DISABLED
	txText.unbind('<Return>')
	MSG2001Btn['state'] = tk.DISABLED
	txText.unbind('<Return>')
	OPEMVBtn['state'] = tk.DISABLED
	txText.unbind('<Return>')

def enableSending():
	sendBtn['state'] = tk.NORMAL
	txText.bind('<Return>', sendCmd)
	MSG2000Btn['state'] = tk.NORMAL
	txText.bind('<Return>', sendMSG2000Cmd)
	MSG2001Btn['state'] = tk.NORMAL
	txText.bind('<Return>', sendMSG2001Cmd)
	OPEMVBtn['state'] = tk.NORMAL
	txText.bind('<Return>', sendOPEMVCmd)

def exitRoot():
	data = {}
	data['autoscroll'] = autoscrollVar.get()
	data['showtimestamp'] = showTimestampVar.get()
	data['showsenttext'] = showSentTextVar.get()
	data['displayhex'] = dispHexVar.get()
	data['lineending'] = lineEndingCbo.current()
	data['baudrateindex'] = baudrateCbo.current()
	data['databits'] = currentPort.bytesize
	data['parity'] = currentPort.parity
	data['stopbits'] = currentPort.stopbits
	data['portindex'] = portCbo.current()
	data['portlist'] = ports
	with open(fname+'.json', 'w') as jfile:
		json.dump(data, jfile, indent=4)
		jfile.close()
	root.destroy()

#-------------------------------------------------- MAIN --------------------------------------------------
if __name__ == '__main__':
	APP_TITLE = 'Serial Monitor'
	BAUD_RATES = (300, 1200, 2400, 4800, 9600, 19200, 38400, 57600, 76800, 115200, 23040, 500000, 1000000, 2000000)
	DATABITS = (serial.FIVEBITS, serial.SIXBITS, serial.SEVENBITS, serial.EIGHTBITS)
	PARITY = (serial.PARITY_EVEN, serial.PARITY_ODD, serial.PARITY_NONE, serial.PARITY_MARK, serial.PARITY_SPACE)
	PARITY_VAL = ('Even', 'Odd', 'None', 'Mark', 'Space')
	STOPBITS = (serial.STOPBITS_ONE, serial.STOPBITS_ONE_POINT_FIVE, serial.STOPBITS_TWO)
	ports = {p.name: p.description for p in list_ports.comports()}
	currentPort = serial.Serial(port=None, baudrate=9600, timeout=0, write_timeout=0)
	portDesc = ''
	sentTexts = []
	sentTextsPtr = 0
	isEndByNL = True
	lastUpdatedBy = 2
	ico = None

	data = {}
	fname = __file__.rsplit('.', 1)[0]
	jfile = None
	try:
		jfile = open(fname+'.json')
		data = json.load(jfile)
	except FileNotFoundError as fnfe:
		pass
	if jfile:
		jfile.close()

	root = tk.Tk()
	root.title(APP_TITLE)
	try:
		ico = tk.PhotoImage(file = fname+'.png')
	except:
		pass
	if ico:
		root.iconphoto(False, ico)
	root.protocol("WM_DELETE_WINDOW", exitRoot)

	autoscrollVar = tk.BooleanVar()
	showTimestampVar = tk.BooleanVar()
	showSentTextVar = tk.BooleanVar()
	dispHexVar = tk.BooleanVar()

	tk.Grid.rowconfigure(root, 0, weight=1)
	tk.Grid.rowconfigure(root, 1, weight=1)
	tk.Grid.rowconfigure(root, 2, weight=999)
	tk.Grid.rowconfigure(root, 3, weight=1)

	tk.Grid.columnconfigure(root, 0, weight=1)
	tk.Grid.columnconfigure(root, 1, weight=1)
	tk.Grid.columnconfigure(root, 2, weight=1)
	tk.Grid.columnconfigure(root, 3, weight=999)
	tk.Grid.columnconfigure(root, 4, weight=1)
	tk.Grid.columnconfigure(root, 5, weight=1)
	tk.Grid.columnconfigure(root, 6, weight=1)

	txText = tk.Entry(root)
	txText.grid(row=0, column=0, columnspan=6, padx=4, pady=8, sticky=tk.N+tk.EW)
	txText.bind('<Up>', upKeyCmd)
	txText.bind('<Down>', downKeyCmd)
	txText.bind('<Button-3>', showTxTextMenu)

	sendBtn = tk.Button(root, width=12, text='Send', state=tk.DISABLED, command=lambda:sendCmd(None))
	sendBtn.grid(row=0, column=6, padx=4, pady=4, sticky=tk.NE)

	MSG2000Btn = tk.Button(root, width=12, text='MSG2000', state=tk.DISABLED, command=lambda:sendMSG2000Cmd(None))
	MSG2000Btn.grid(row=1, column=0, padx=4, pady=4, sticky=tk.NE)
	MSG2001Btn = tk.Button(root, width=12, text='MSG2001', state=tk.DISABLED, command=lambda:sendMSG2001Cmd(None))
	MSG2001Btn.grid(row=1, column=1, padx=4, pady=4, sticky=tk.NE)
	OPEMVBtn = tk.Button(root, width=12, text='OP EMV', state=tk.DISABLED, command=lambda:sendOPEMVCmd(None))
	OPEMVBtn.grid(row=1, column=2, padx=4, pady=4, sticky=tk.NE)

	rxText = tkscroll.ScrolledText(root, height=20, state=tk.DISABLED, font=('Courier', 10), wrap=tk.WORD)
	rxText.grid(row=2, column=0, columnspan=7, padx=4, sticky=tk.NSEW)
	rxText.bind('<Button-3>', showRxTextMenu)

	autoscrollCbt = tk.Checkbutton(root, text='Autoscroll', variable=autoscrollVar, onvalue=True, offvalue=False)
	autoscrollCbt.grid(row=3, column=0, padx=4, pady=4, sticky=tk.SW)
	di = data.get('autoscroll')
	if di != None:
		autoscrollVar.set(di)

	showTimestampCbt = tk.Checkbutton(root, text='Show timestamp', variable=showTimestampVar, onvalue=True, offvalue=False)
	showTimestampCbt.grid(row=3, column=1, padx=4, pady=4, sticky=tk.SW)
	di = data.get('showtimestamp')
	if di != None:
		showTimestampVar.set(di)

	showSentTextCbt = tk.Checkbutton(root, text='Show sent text', variable=showSentTextVar, onvalue=True, offvalue=False)
	showSentTextCbt.grid(row=3, column=2, padx=4, pady=4, sticky=tk.SW)
	di = data.get('showsenttext')
	if di != None:
		showSentTextVar.set(di)

	portCbo = ttk.Combobox(root, width=10)
	portCbo.grid(row=3, column=3, padx=4, pady=4, sticky=tk.SE)
	portCbo.bind('<<ComboboxSelected>>', changePort)
	portCbo['values'] = sorted(ports)
	if len(ports) > 0:
		portCbo['state'] = 'readonly'
		portCbo.set('Select port')
	else:
		portCbo['state'] = tk.DISABLED
		portCbo.set('No port')

	lineEndingCbo = ttk.Combobox(root, width=14, state='readonly')
	lineEndingCbo.grid(row=3, column=4, padx=4, pady=4, sticky=tk.SE)
	lineEndingCbo['values'] = ('No line ending', 'Newline', 'Carriage return', 'Both CR & NL')
	di = data.get('lineending')
	if di != None:
		lineEndingCbo.current(di)
	else:
		lineEndingCbo.current(0)

	baudrateCbo = ttk.Combobox(root, width=12, state='readonly')
	baudrateCbo.grid(row=3, column=5, padx=4, pady=4, sticky=tk.SE)
	baudrateCbo['values'] = list(str(b) + ' baud' for b in BAUD_RATES)
	baudrateCbo.bind('<<ComboboxSelected>>', changeBaudrate)
	di = data.get('baudrateindex')
	if di != None:
		baudrateCbo.current(di)
		currentPort.baudrate = BAUD_RATES[di]
	else:
		baudrateCbo.current(4) # 9600 baud
		currentPort.baudrate = BAUD_RATES[4]

	clearBtn = tk.Button(root, width=12, text='Clear output', command=clearOutputCmd)
	clearBtn.grid(row=3, column=6, padx=4, pady=4, sticky=tk.SE)

	txTextMenu = tk.Menu(txText, tearoff=0)
	txTextMenu.add_command(label='Cut', accelerator='Ctrl+X', command=lambda:txText.event_generate('<<Cut>>'))
	txTextMenu.add_command(label='Copy', accelerator='Ctrl+C', command=lambda:txText.event_generate('<<Copy>>'))
	txTextMenu.add_command(label='Paste', accelerator='Ctrl+V', command=lambda:txText.event_generate('<<Paste>>'))

	rxTextMenu = tk.Menu(rxText, tearoff=0)
	rxTextMenu.add_command(label='Copy', accelerator='Ctrl+C', command=lambda:rxText.event_generate('<<Copy>>'))
	rxTextMenu.add_separator()
	rxTextMenu.add_command(label='Close active port', command=closePort)
	rxTextMenu.add_separator()
	rxTextMenu.add_checkbutton(label='Display in hexadecimal code', onvalue=True, offvalue=False, variable=dispHexVar)
	rxTextMenu.add_separator()
	rxTextMenu.add_command(label='Port setting', command=setting)

	listPortsPolling()

	root.update()
	sw = root.winfo_screenwidth()
	sh = root.winfo_screenheight()
	rw = root.winfo_width()
	rh = root.winfo_height()
	root.minsize(rw, 233)
	root.geometry(f'{rw}x{rh}+{int((sw-rw)/2)}+{int((sh-rh)/2)-30}')
	wtx =" "
	writeConsole(wtx, 2)

	di = data.get('displayhex')
	if di != None:
		dispHexVar.set(di)
	di = data.get('databits')
	if di != None:
		currentPort.bytesize = di
	di = data.get('parity')
	if di != None:
		currentPort.parity = di
	di = data.get('stopbits')
	if di != None:
		currentPort.stopbits = di
	di = data.get('portindex')
	if di != None and di != -1 and data.get('portlist') == ports:
		portCbo.current(di)
		changePort(None)

	root.mainloop()