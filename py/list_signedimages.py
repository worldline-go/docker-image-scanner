import mysql.connector, os
from mysql.connector import Error
from ast import literal_eval
from modules import colours

class SignedImage:
    def __init__(self, host, user, pwd):
        self.dbconnect = mysql.connector.connect(host=host,
                        database='notaryserver',
                        user=user,
                        password=pwd,
                        connect_timeout=5
                        )

        self.cursor = self.dbconnect.cursor()

    def get_image_list(self):
        """
        Returns all scanned and signed images from notary database.
        :param notary[0]: Created date of the signed image on database column
        :param notary[1]: Full image name of the signed image on database column
        :param {tag}, {value['hashes']}: Image tag and hashid value of the signed source
        :param unique_images, Keeps image hash values as an unordered collection
        """
        try:
            if self.dbconnect.is_connected():
                query = "select created_at, gun, JSON_EXTRACT(data, '$.signed.targets') from tuf_files where role='targets';"
                self.cursor.execute(query)
                signedData = self.cursor.fetchall()

                if signedData:
                    unique_images = set()
                    for notary in signedData:
                        ImageHash = literal_eval(notary[2].decode()) # cleans "bytearray" from json data
                        for tag, value in ImageHash.items():
                            hashes_data = f"{notary[0]} {notary[1]}:{tag} {value['hashes']}"
                            if f"{value['hashes']}" in unique_images:
                                continue
                            unique_images.add(f"{value['hashes']}")
                            print(hashes_data)
                    print(f"Total signed image: {len(unique_images)}")
                else:
                    print("No found any signed image to list!", signedData)

        except Error:
            raise
        finally:
            if self.dbconnect.is_connected():
               self.cursor.close()
               self.dbconnect.close()

def access_main():
    host = os.environ.get('NOTARY_SERVER_IP')
    user = os.environ.get('NOTARY_DB_USER')
    pwd =  os.environ.get('NOTARY_DB_PASS')

    if (host is None or host == ''):
       raise Exception(colours.red("check NOTARY_SERVER_IP env variable!"))
    elif (user is None or user == ''):
        raise Exception(colours.red("check NOTARY_DB_USER env variable!"))
    elif (pwd is None or pwd == ''):
       raise Exception(colours.red("check NOTARY_DB_PASS env variable!"))

    passCredential=SignedImage(host, user, pwd)
    passCredential.get_image_list()

if __name__ == "__main__":
  access_main()
