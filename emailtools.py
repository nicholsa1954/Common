import re

### Source: https://medium.com/@python-javascript-php-html-css/the-best-regular-expression-for-email-address-verification-42bf83ba2885
def ValidateEmail(email):
    if isinstance(email, float) or email == "" or email != email: return "" # in case email is NaN
    # Regular expression for email validation
    regex  = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    # Return true if email matches regex, false otherwise
    
    if re.match(regex, email) is not None: return email
    else:
        return (f'Invalid email: {email}')