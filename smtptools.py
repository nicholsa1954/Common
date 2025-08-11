import smtplib
import ssl
from email.message import EmailMessage
from email.utils import make_msgid
import mimetypes

def SendEmailSecureWithImage(app_passwd, subject, sender, recipients, cc, bcc, plain_text, html_text, smtp_server, 
        smtp_port, image_path, image_width=320, image_height=400):
    if image_path is None:
        raise ValueError("image_path cannot be None")
    try:
        context = ssl.create_default_context()
        msg = EmailMessage()
        
        # generic email headers
        msg['Subject'] = subject
        msg['From'] = sender
        msg['To'] =  ', '.join(recipients)
        msg['Cc'] =  ', '.join(cc)
        ### Don't do this unless you want to publish the bcc list
        # msg['Bcc'] = ', '.join(bcc)        
        # set the plain text body
        msg.set_content(plain_text)

        # now create a Content-ID for the image
        image_cid = make_msgid(domain='gmail.com')
        # if `domain` argument isn't provided, it will 
        # use your computer's name

# set an alternative html body
        msg.add_alternative("""\
        <html>
            <body>
                <p>{html_text}</p>
                <img src="cid:{image_cid}" width={image_width} height={image_height}/>
            </body>
        </html>
        """.format(html_text=html_text,
            image_cid=image_cid[1:-1], 
            image_width=image_width, 
            image_height=image_height), 
            subtype='html')        

        with open(image_path, 'rb') as img:
            # know the Content-Type of the image
            maintype, subtype = mimetypes.guess_type(img.name)[0].split('/')

            # attach it
            msg.get_payload()[1].add_related(img.read(), 
                                                maintype=maintype, 
                                                subtype=subtype, 
                                                cid=image_cid)
            
        with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context) as server:
            server.login(sender, app_passwd)
            # server.set_debuglevel(1)
            # include the cc and bcc list here but don't put bcc in the msg headers
            server.sendmail(sender, (recipients + cc + bcc), msg.as_string())
            print("Secure email sent successfully!")
    except smtplib.SMTPException as e:
        print(f"SMTP error occurred: {e}")
    except Exception as e:
        print(f"General error: {e}")    