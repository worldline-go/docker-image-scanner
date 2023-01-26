# docker-image-scanner

`#DevSecOPS`

![](https://i.paste.pics/d773a6b5e5b964435e2056600afb56ca.png "Vaşak")

## Summary
Scans docker images to inspect any possible malware/rootkit, wrong compliance cases or OS package/library vulnerabilities before sign and push them into the docker registry. In this way it provides the image consistency&integrity perspective with signing process.

``Attention!`` This project cannot give any guarantee which target image is %100 secure but helps to understand, and identify the security issues. Please carefully review related reports (malware, compliance and package scanning) or get help from someone who can contribute to understand security issues on reporting side.


## Features
Backdoor and Malware Scanning<br>
Vulnerability and Compliance Audit Checks<br>
Image Sign with [Notary](https://docs.docker.com/notary/service_architecture/)<br>
Detailed Technical PDF Reports<br>
Quarantine & Whitelist<br>
Dynamic Registry Integration<br>
Auto Clean for Container & Unused Images<br>
Unlimited scanning (Don't sign and push image(s) if it is signed before)<br>
Gitlab Pipeline Compatibility

## Usage

**1)** Create merge request which contain image name(s) with tag in "**sources**" file that you want to scan and sign.

**Format**<br>
<image_name:tag>

**Example**<br>
golang:1.13.4-buster<br>

Note that it auto adds the "latest" tag if you don't add anything next to the image name in source file.<br>


**2)** Go to the pipeline page to see and check the steps when MR is merged to the master branch. In here you should review 3 most important stages which named **Compliance**, **Malware** and **Package** scanning parts before click to sign button. This decision making part can be either done with DevOPS or a Developer who works in same or cross team. Click to `promote:sign` button only if all reports seems to be safe and decision making is positive.


** malware and compliance's detail warning logs stores in artifact area as a PDF file. Check the following picture to see an example:


![](https://i.paste.pics/91f33162b7e6630f9161208b3e4d9558.png)


## Pre-Build Image
[This repo](https://<docker-hub-address>
) is responsible to buil a pipeline image for this project which contains pre-installed packages, python libraries and other settings. That approach helps to make this pipeline is more faster and keeps it less complicated.

Please use there to update python libraries and also make other specified settings.

## Target Registry

This project can only push signed image(s) in target registry which defined in variable area from this pipeline but it is also possible to change default registry source if you set following variables.<br>
> Settings > CI/CD > Variables: <br>
`$REGISTRY_USER`
`$REGISTRY_PASS`
`$REGISTRY_SERVER`

## Custom Entrypoint

You can set following variable to pass a custom entrypoint for a container during image scanning progress.
> Settings > CI/CD > Variables: <br>
`$ENTRYPOINT`

Note that `/bin/sh` uses as an entrypoint by default if custom variable is not defined.

## Technologies

Following open source technologies are used in this project.<br>

- Python3<br>
- Docker Python SDK<br>
- Alpine Linux<br>
- Gitlab CI/CD - Pipeline<br>
- Lynis  (Security auditing and hardening tool, for UNIX-based systems )<br>
- RKhunter (Security monitoring tool which is flexible with POSIX compliant systems. Scans for rootkits, and other possible vulnerabilities )<br>
- Trivy (Check OS package and libraries to find possible vulnerabilities) <br>
- Docker Notary (Sign & Key Management)
