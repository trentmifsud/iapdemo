import os,sys

from flask import Flask, request, jsonify, redirect
#from google.cloud import storage


app = Flask(__name__)
CERTS = None
AUDIENCE = None


def certs():
    """Returns a dictionary of current Google public key certificates for
    validating Google-signed JWTs. Since these change rarely, the result
    is cached on first request for faster subsequent responses.
    """
    import requests

    global CERTS
    if CERTS is None:
        response = requests.get(
            'https://www.gstatic.com/iap/verify/public_key'
        )
        CERTS = response.json()
    return CERTS


def get_metadata(item_name):
    """Returns a string with the project metadata value for the item_name.
    See https://cloud.google.com/compute/docs/storing-retrieving-metadata for
    possible item_name values.
    """
    import requests

    endpoint = 'http://metadata.google.internal'
    path = '/computeMetadata/v1/project/'
    path += item_name
    response = requests.get(
        '{}{}'.format(endpoint, path),
        headers={'Metadata-Flavor': 'Google'}
    )
    metadata = response.text
    return metadata


def audience():
    """Returns the audience value (the JWT 'aud' property) for the current
    running instance. Since this involves a metadata lookup, the result is
    cached when first requested for faster future responses.
    """
    global AUDIENCE
    if AUDIENCE is None:
        project_number = get_metadata('numeric-project-id')
        project_id = get_metadata('project-id')
        AUDIENCE = '/projects/{}/apps/{}'.format(
            project_number, project_id
        )
    return AUDIENCE

@app.route("/userinfo")  # New route specifically for user info
def user_info():
     assertion = request.headers.get('X-Goog-IAP-JWT-Assertion')
     email, id = validate_assertion(assertion)

     if email:
         user_info = {'email': email, 'id': id} # Add other claims as needed
         return jsonify(user_info)
     else:
         return jsonify({'error': 'IAP authentication failed'}), 401

# Improved error handling in validate_assertion
def validate_assertion(assertion):
    from jose import jwt
    from jose.exceptions import JWTError, ExpiredSignatureError, JWTClaimsError

    try:
        info = jwt.decode(
            assertion,
            certs(),
            algorithms=['ES256'],
            audience=audience()
        )
        return info['email'], info['sub']
    except ExpiredSignatureError:
        print("JWT has expired", file=sys.stderr)
        return None, None
    except JWTClaimsError as e:
        print(f"JWT claim error: {e}", file=sys.stderr)
        return None, None
    except JWTError as e:
         print(f"JWT validation failed: {e}", file=sys.stderr)
         return None, None
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)  # Catch other exceptions
        return None, None



@app.route('/', methods=['GET'])
def say_hello():
    assertion = request.headers.get('X-Goog-IAP-JWT-Assertion')
    email, id = validate_assertion(assertion)

    if email:
        user_info = {'email': email, 'id': id}
        return jsonify(user_info) # Return JSON response
    else:
        return jsonify({'error': 'IAP authentication failed'}), 401 # 401 Unauthorized
'''
@app.route("/images/<filename>")
def serve_image(filename):
    # ... Authentication and authorization logic ...
    user_id = get_user_id(request) # Retrieve user ID from session data
    permissions = get_user_permissions(user_id) # Get user's permissions
    
    if has_permission(permissions, 'read_images'):  # Replace with your permission check logic
        blob = bucket.blob(filename)
        if blob.exists():
            signed_url = generate_signed_url(blob) # Generate signed URL
            return redirect(signed_url)
        else:
            return "Image not found", 404
    else:
        return "Unauthorized", 401
'''
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))