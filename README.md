# Threads Publishing API Python Sample App

You can use this Sample App to test the [Threads API](https://developers.facebook.com/docs/threads).

1. Make sure that you are using the APP ID and Secret defined for the Threads API of your app. These ARE not the same as the regular app ID and app secret.
2. Make sure you add your application's redirect URL e.g. https://threads-sample.meta:8000/callback, to your app's redirect callback URLs in the app dashboard.

## Required software

In order to run the Sample App you will need to install some required software, as follows:

1. Set up your environment

    If you're using conda...
    ```sh
    conda create --name threads_py python=3.12
    conda activate threads_py
    ```

    Install dependencies
    ```sh
    poetry install --with dev,test
    ```

2. Create a new file called `.env` and copy/paste all the environment variables from `.env.template`. Replace any environnment variables that have placeholders, such as APP_ID.

3. Map a domain to your local machine for local development
    * Note: Threads apps do not support redirect URLs with using `localhost` so you must map a domain to test locally this Sample App.
    * Map a new entry in your hosts file to the domain that you will use to test the Sample App e.g. `threads-sample.meta`.
    * If you're using a Linux or Mac, this will be your `/etc/hosts` file.
    * Add an entry like so:
        ```
        127.0.0.1   threads-sample.meta
        ```
    * This will map threads-sample.meta to localhost, so you may visit https://threads-sample.meta:8000 to see the Threads Sample App.
    * This domain must match the one defined in your `.env` file as the value of the `HOST` variable.

4. Create an OpenSSL Cert
    * OAuth redirects are only supported over HTTPS so you must create an SSL certificate
    * `mkcert threads-sample.meta` - This will create pem files for SSL.
    * You will see `threads-sample.meta.pem` and `threads-sample.meta-key.pem `files generated.
    * If you are using a host that is different than `threads-sample.meta` then replace it with your specific domain.

5. Run the Sample App
    * Run `python threads/main.py` from the command line.
    * Once the Sample App starts running, go to https://threads-sample.meta:8000 to test the workflow.
    * If you are using a different domain or port then replace those values accordingly.
