do_deploy:append() {
    # Disable HDMI out since we use the DSI screen
    echo "hdmi_blanking=1" >> ${DEPLOYDIR}/bootfiles/config.txt
    
    # Disable activity and power LEDs to save power and reduce signature in the field
    echo "dtparam=act_led_trigger=none" >> ${DEPLOYDIR}/bootfiles/config.txt
    echo "dtparam=act_led_activelow=off" >> ${DEPLOYDIR}/bootfiles/config.txt
    echo "dtparam=pwr_led_trigger=none" >> ${DEPLOYDIR}/bootfiles/config.txt
    echo "dtparam=pwr_led_activelow=off" >> ${DEPLOYDIR}/bootfiles/config.txt
    
    # Ensure USB is enabled for the AIO v2 board
    echo "dtoverlay=dwc2,dr_mode=host" >> ${DEPLOYDIR}/bootfiles/config.txt
}
