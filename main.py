import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, List, Tuple

class InFlightMonitor:
    """Monitors in-flight events and sends alerts for unsafe parameters"""
    
    def __init__(self, email_config: Dict[str, str]):
        """
        Initialize the monitor with email configuration
        
        Args:
            email_config: Dictionary containing email settings
        """
        self.email_config = email_config
        
        # Define safety margins for different parameters
        self.safety_margins = {
            'altitude': {'min': 0, 'max': 41000, 'unit': 'feet'},
            'airspeed': {'min': 120, 'max': 550, 'unit': 'knots'},
            'vertical_speed': {'min': -2000, 'max': 2000, 'unit': 'ft/min'},
            'heading': {'min': 0, 'max': 359, 'unit': 'degrees'},
            'fuel_quantity': {'min': 500, 'max': 50000, 'unit': 'lbs'},
            'engine_temperature': {'min': 0, 'max': 950, 'unit': '°C'},
            'oil_pressure': {'min': 50, 'max': 120, 'unit': 'psi'},
            'cabin_pressure': {'min': 14, 'max': 14.7, 'unit': 'psi'},
            'outside_air_temperature': {'min': -60, 'max': 50, 'unit': '°C'},
            'wind_speed': {'min': 0, 'max': 100, 'unit': 'knots'},
            'visibility': {'min': 0.5, 'max': 10, 'unit': 'miles'},
            'radar_altitude': {'min': 0, 'max': 2500, 'unit': 'feet'}
        }
        
        # Modem specifications
        self.modem_specs = {
            'modem_model': 'AV-Comm XR-9000',
            'frequency_band': 'L-Band (1-2 GHz)',
            'data_rate': '64 kbps - 2 Mbps',
            'transmit_power': '5-25 Watts',
            'receiver_sensitivity': '-120 dBm',
            'modulation': 'BPSK, QPSK, 8PSK, 16QAM',
            'encryption': 'AES-256',
            'satellite_system': 'Iridium Certus, Inmarsat SwiftBroadband'
        }
    
    def check_parameter(self, param_name: str, value: float) -> Tuple[bool, str]:
        """
        Check if a parameter is within safety margins
        
        Returns:
            Tuple of (is_safe, message)
        """
        if param_name not in self.safety_margins:
            return True, f"Parameter '{param_name}' not in safety margins database"
        
        margins = self.safety_margins[param_name]
        
        if value < margins['min']:
            return False, f"⚠️ {param_name.upper()}: {value} {margins['unit']} is BELOW minimum safe value of {margins['min']} {margins['unit']}"
        elif value > margins['max']:
            return False, f"⚠️ {param_name.upper()}: {value} {margins['unit']} is ABOVE maximum safe value of {margins['max']} {margins['unit']}"
        else:
            return True, f"✓ {param_name.upper()}: {value} {margins['unit']} is within safe range [{margins['min']}-{margins['max']}]"
    
    def check_all_parameters(self, flight_data: Dict[str, float]) -> Tuple[bool, List[str]]:
        """
        Check all flight parameters against safety margins
        
        Returns:
            Tuple of (all_safe, list_of_alert_messages)
        """
        alerts = []
        all_safe = True
        
        for param, value in flight_data.items():
            is_safe, message = self.check_parameter(param, value)
            if not is_safe:
                all_safe = False
                alerts.append(message)
            else:
                print(message)
        
        return all_safe, alerts
    
    def send_alert_email(self, flight_data: Dict[str, float], alerts: List[str]) -> bool:
        """
        Send email alert to monitoring service with modem specifications
        """
        if not self.email_config.get('enabled', True):
            print("Email sending is disabled (testing mode)")
            return False
        
        try:
            # Create email message
            subject = f"⚠️ URGENT: In-Flight Safety Alert - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            # Build email body
            body = self._build_email_body(flight_data, alerts)
            
            # Create MIME message
            message = MIMEMultipart()
            message['From'] = self.email_config['from_email']
            message['To'] = self.email_config['to_email']
            message['Subject'] = subject
            
            message.attach(MIMEText(body, 'html'))
            
            # Send email using SMTP
            context = ssl.create_default_context()
            
            with smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port']) as server:
                server.starttls(context=context)
                server.login(self.email_config['username'], self.email_config['password'])
                server.send_message(message)
            
            print(f"\n✓ Alert email sent successfully to {self.email_config['to_email']}")
            return True
            
        except Exception as e:
            print(f"\n✗ Failed to send email: {str(e)}")
            return False
    
    def _build_email_body(self, flight_data: Dict[str, float], alerts: List[str]) -> str:
        """Build HTML email body with alerts and modem specifications"""
        
        # Modem specs HTML table
        modem_html = "<h3>📡 Modem Specifications</h3>"
        modem_html += "<table border='1' cellpadding='5' style='border-collapse: collapse;'>"
        for key, value in self.modem_specs.items():
            modem_html += f"<tr><td style='padding: 8px;'><strong>{key.replace('_', ' ').title()}</strong></td>"
            modem_html += f"<td style='padding: 8px;'>{value}</td></tr>"
        modem_html += "</table>"
        
        # Flight data table
        flight_html = "<h3>✈️ Current Flight Parameters</h3>"
        flight_html += "<table border='1' cellpadding='5' style='border-collapse: collapse;'>"
        flight_html += "<tr style='background-color: #f2f2f2;'><th>Parameter</th><th>Value</th><th>Safety Range</th><th>Status</th></tr>"
        
        for param, value in flight_data.items():
            margins = self.safety_margins.get(param, {'min': 'N/A', 'max': 'N/A', 'unit': ''})
            unit = margins.get('unit', '')
            min_val = margins.get('min', 'N/A')
            max_val = margins.get('max', 'N/A')
            
            is_safe, _ = self.check_parameter(param, value)
            status = "✅ SAFE" if is_safe else "❌ UNSAFE"
            color = "#4CAF50" if is_safe else "#f44336"
            
            flight_html += f"<tr>"
            flight_html += f"<td style='padding: 8px;'><strong>{param.replace('_', ' ').title()}</strong></td>"
            flight_html += f"<td style='padding: 8px;'>{value} {unit}</td>"
            flight_html += f"<td style='padding: 8px;'>{min_val} - {max_val} {unit}</td>"
            flight_html += f"<td style='padding: 8px; color: {color};'>{status}</td>"
            flight_html += f"</tr>"
        flight_html += "</table>"
        
        # Alerts section
        alerts_html = "<h3>⚠️ ALERTS DETECTED</h3>"
        alerts_html += "<ul>"
        for alert in alerts:
            alerts_html += f"<li style='color: #f44336;'>{alert}</li>"
        alerts_html += "</ul>"
        
        # Complete email body
        complete_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                h3 {{ color: #333; }}
                table {{ margin: 10px 0; }}
                .header {{ background-color: #ff4444; color: white; padding: 10px; text-align: center; }}
            </style>
        </head>
        <body>
            <div class='header'>
                <h2>🚨 URGENT AVIATION SAFETY ALERT</h2>
                <p>Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
            </div>
            {alerts_html}
            {flight_html}
            {modem_html}
            <hr>
            <p><em>This is an automated alert from the Aviation In-Flight Monitoring System.</em></p>
            <p><em>Please investigate immediately and take appropriate action.</em></p>
        </body>
        </html>
        """
        
        return complete_body
    
    def process_flight_data(self, flight_data: Dict[str, float]) -> None:
        """
        Process flight data and send alerts if safety margins are violated
        """
        print("\n" + "="*60)
        print("🔍 ANALYZING IN-FLIGHT DATA...")
        print("="*60)
        
        all_safe, alerts = self.check_all_parameters(flight_data)
        
        if not all_safe:
            print("\n" + "="*60)
            print("⚠️ SAFETY MARGINS VIOLATED!")
            print("="*60)
            
            for alert in alerts:
                print(alert)
            
            print("\n📧 Sending email alert to monitoring service...")
            self.send_alert_email(flight_data, alerts)
        else:
            print("\n✅ All parameters within safety margins. No alert needed.")


# Demo and testing function
def main():
    """
    Main function to demonstrate the In-Flight Monitor
    """
    
    # Email configuration (Replace with actual credentials for real use)
    email_config = {
        'enabled': False,  # Set to True to actually send emails
        'smtp_server': 'smtp.gmail.com',
        'smtp_port': 587,
        'from_email': 'aviation_monitor@example.com',
        'to_email': 'monitoring_service@aviation.com',
        'username': 'your_email@gmail.com',
        'password': 'your_app_password'  # Use app-specific password for Gmail
    }
    
    # Create monitor instance
    monitor = InFlightMonitor(email_config)
    
    # Test case 1: Normal flight data (all safe)
    print("\n" + "="*60)
    print("TEST CASE 1: NORMAL FLIGHT OPERATIONS")
    print("="*60)
    
    normal_flight = {
        'altitude': 35000,
        'airspeed': 450,
        'vertical_speed': 500,
        'heading': 270,
        'fuel_quantity': 15000,
        'engine_temperature': 850,
        'oil_pressure': 85,
        'cabin_pressure': 14.5,
        'outside_air_temperature': -45,
        'wind_speed': 25,
        'visibility': 8,
        'radar_altitude': 0
    }
    
    monitor.process_flight_data(normal_flight)
    
    # Test case 2: Unsafe flight data (should trigger email)
    print("\n" + "="*60)
    print("TEST CASE 2: UNSAFE CONDITIONS DETECTED")
    print("="*60)
    
    unsafe_flight = {
        'altitude': 42000,  # Too high (max 41000)
        'airspeed': 600,    # Too fast (max 550)
        'vertical_speed': 3000,  # Too fast (max 2000)
        'heading': 270,
        'fuel_quantity': 300,  # Too low (min 500)
        'engine_temperature': 1000,  # Too hot (max 950)
        'oil_pressure': 40,  # Too low (min 50)
        'cabin_pressure': 13.5,  # Too low (min 14)
        'outside_air_temperature': -65,  # Too cold (min -60)
        'wind_speed': 120,  # Too high (max 100)
        'visibility': 0.2,  # Too low (min 0.5)
        'radar_altitude': 0
    }
    
    monitor.process_flight_data(unsafe_flight)
    
    # Test case 3: Partial violation
    print("\n" + "="*60)
    print("TEST CASE 3: MULTIPLE VIOLATIONS")
    print("="*60)
    
    multiple_violations = {
        'altitude': 45000,
        'airspeed': 480,
        'vertical_speed': -2500,
        'heading': 360,
        'fuel_quantity': 10000,
        'engine_temperature': 925,
        'oil_pressure': 110,
        'cabin_pressure': 14.6,
        'outside_air_temperature': -30,
        'wind_speed': 55,
        'visibility': 5,
        'radar_altitude': 3000  # Too high for radar altimeter
    }
    
    monitor.process_flight_data(multiple_violations)


if __name__ == "__main__":
    main()