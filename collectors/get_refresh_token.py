from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/drive.file"]

def main():
    flow = InstalledAppFlow.from_client_secrets_file("oauth_client.json", SCOPES)

    # Opens browser, listens on localhost, captures the redirect automatically.
    creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")

    print("\nREFRESH_TOKEN:\n")
    print(creds.refresh_token)

if __name__ == "__main__":
    main()
