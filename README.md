### RFID Shop Check In (Headless with Raspberry Pi and Omnikey)
Tracks shop sign in actions via member RCS ID. Success scan actions will be logged to [Google Sheet]("https://docs.google.com/spreadsheets/d/1NcW4DqQr9W4dRV4CPHQSa4G9ISCfxIq2rJ4OiikBKzg/edit?usp=sharing"). 

In order to sign up as a new member, please scan and then fill out [this form]("https://docs.google.com/forms/d/e/1FAIpQLSdJYKL_i3sIDvAICB_IUcCo1736gCUuLAM4tFcBlLQT5lPboA/viewform"). When filling out the form, you must select your correspond UID based on the last time you scanned (If you forgot the time, you can always scan again).

###Installation (For Development)
Connect to the Pi:
`ssh admin@<ip_address>`
You can check the ip_address by `arp -a	` and looking for the Physical Adress that is in form of `b8-27-eb`, copy the correspond number from Internet address column, it is the ip_address you need.

Setup systemctl, library and enable ssh:
```
sudo apt update
sudo apt install python3-gpiozero python3-pip python3-pyscard -y
sudo systemctl enable ssh
```
Install **main.py** into the pi:
```
 mkdir ShopSignIn
 cd ShopSignIn
 nano main.py
```
Copy the code from main.py and paste into the file you just created.  `Ctrl-O`, `Enter`, `Ctrl-X` to Exit.

Next, run
`sudo nano /etc/systemd/system/shop_signin.service`

Copy and Paste code from .service file.

To start the headless system, run the following command:
```
sudo systemctl daemon-reload
sudo systemctl enable shop_signin.service
sudo systemctl start shop_signin.service
```
You can check the status of the system by 
`sudo systemctl status shop_signin.service`.

You can stop the system by 
`sudo systemctl stop shop_signin.service`.

###Deployment
If you ever decided to integrate LED in your system. Remember to connect
**RED** to **GPIO 17**
**YELLOW** to **GPIO 27**
**GREEN** to **GPIO 22**

For the webapp, you can always created new Google Sheet or Google Form  with the same structure with the shared files. After that `Extensionions --> App Scripts`  and paste the code from our .gs file.  ***Remember to link Google Form with our Google Sheet***.

Additionally, for this two files to interact with others precisely, in App Scripts, go to **Triggers**, and set:
onSheetChange function -- On edit	
onFormSubmit -- On Form Submit 
onSheetChange -- On Change