#!/bin/bash
#This is from https://stackoverflow.com/questions/66480203/pyvisa-not-listing-usb-instrument-on-linux
# It worked on linux 22.04 to allow visa use of the scope without ni-visa
sudo echo 'SUBSYSTEM=="usb", MODE="0666", GROUP="usbusers"' >> /etc/udev/rules.d/99-com.rules
echo "PLEASE RESTART YOUR SYSTEM FOR FIX TO WORK"
