import subprocess
from modules import dockerutils
from modules import time, logs

class trivy:
    def run_trivy_scan(image, trivy):
        """
        Clear trivy cache and start a scan process on image from quarantine.
        This function focus on OS packages and application
        libraries(python, golang, java) to find their possible vulnerabilities.
        Trivy binary is embedded in pipeline image.
        """
        try:
            severity = "HIGH,CRITICAL"
            scan_command = f"{trivy} image --clear-cache && {trivy} image --severity {severity} {image} --debug"
            scan_result = subprocess.Popen(
            [f"{scan_command}"],
                        shell=True, encoding='utf-8')
            scan_result.wait()

            if scan_result.returncode != 0:
                fallback_scan_result = subprocess.Popen(
                    [f"{scan_command} --offline-scan"],
                                shell=True, encoding='utf-8')
                fallback_scan_result.wait()

                if fallback_scan_result.returncode != 0:
                    raise Exception(scan_result)
                else:
                    print("Fallback: scanned by offline method!")

        except subprocess.CalledProcessError:
            raise

def start_package_scan():
    images = dockerutils.command.get_quarantined_images()
    image_count = len(images)

    if images is None:
        raise Exception("cannot find any image in quarantine!")
    else:
        for image in images:
            logs.event.logger.info("[1/1] OS Package & Application Library Checking: %s %s", '\nImage Name:', image)
            trivy.run_trivy_scan(image, trivy="/opt/trivy")
            time.WaitNextProcess.set_sleep_time(3, image_count)
if __name__ == "__main__":
    start_package_scan()
