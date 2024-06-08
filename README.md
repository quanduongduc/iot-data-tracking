<a name="readme-top"></a>

<!-- PROJECT SHIELDS -->
<!--
*** I'm using markdown "reference style" links for readability.
*** Reference links are enclosed in brackets [ ] instead of parentheses ( ).
*** See the bottom of this document for the declaration of the reference variables
*** for contributors-url, forks-url, etc. This is an optional, concise syntax you may use.
*** https://www.markdownguide.org/basic-syntax/#reference-style-links
-->
[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![LinkedIn][linkedin-shield]][linkedin-url]


<!-- PROJECT LOGO AND TITLE -->
<p align="center">
  <a href="https://github.com/quanduongduc/iot-data-tracking">
    <img src="images/logo.png" alt="Logo" width="100" height="100">
  </a>

  <h2 align="center">Rtdt</h2>
  <p align="center">
    Real-time Data tracking
    <br />
    <a href="https://github.com/quanduongduc/iot-data-tracking"><strong>Check the Documentation »</strong></a>
    <br />
    <a href="https://github.com/quanduongduc/iot-data-tracking">View a Live Demo</a>
    •
    <a href="https://github.com/quanduongduc/iot-data-tracking/issues/new?template=bug_report.md">Report a Bug</a>
    •
    <a href="https://github.com/quanduongduc/iot-data-tracking/issues/new?template=feature_request.md">Request a Feature</a>
  </p>
</p>

<!-- TABLE OF CONTENTS -->
<details open="open">
  <summary>Table of Contents</summary>
  <ol>
    <li><a href="#about">About This Project</a></li>
    <li><a href="#start">Getting Started</a></li>
    <li><a href="#use">Usage Guidelines</a></li>
    <li><a href="#todos-section">TODOS</a></li>
    <li><a href="#contrib-section">Contribution Guidelines</a></li>
    <li><a href="#contact-section">Contact Details</a></li>
  </ol>
</details>

<!-- ABOUT THE PROJECT -->
## <a name="about"></a>About This Project
![image](https://github.com/quanduongduc/iot-data-tracking/assets/59951771/0e5e9237-5c3f-46c1-a001-d43b50afd1c2)

[🔝 Back to Top](#readme-top-anchor)

<!-- GETTING STARTED -->
## <a name="start"></a>Getting Started

To get the project up and running 
**Prerequisite**

Before proceeding, ensure you meet the following requirements:

1. Add your AWS credentials to the AWS configuration.
1. Install Pulumi. You can find installation instructions [here](https://www.pulumi.com/docs/get-started/install/).
3. Install the dependencies listed in `requirements/local.txt`.

**Usage**

Once you've fulfilled these prerequisites, you can proceed with deploying the infrastructure using Pulumi.
To deploy the infrastructure, you need to have Pulumi installed and configured with your AWS credentials. Then, you can run the following command in the infrastructure directory:

This command will preview the changes to be made and, after confirmation, apply the changes. You can see the status of your stack at any time with the `pulumi stack` command.

```
cmd pulumi up
```

**Topology**

![image](https://github.com/quanduongduc/iot-data-tracking/assets/59951771/73440cc0-1029-4c86-ac4a-b89a978f9860)

### Setting up:

* Install the required tools:


<!-- TODOS -->
## <a name="todos-section"></a>To-Do List
- [x] Change to Fargate
- [x] Use SPOT instances with robust unavailability management for saving cost
- [ ] Replace the NAT with VPC endpoints
- [ ] Adopt Spark for data processor (Experiment only)
- [ ] Try Kafka source and sink connectors (Experiment only)


<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
[contributors-shield]: https://img.shields.io/github/contributors/othneildrew/Best-README-Template.svg?style=for-the-badge
[contributors-url]: https://github.com/quanduongduc/iot-data-tracking/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/othneildrew/Best-README-Template.svg?style=for-the-badge
[forks-url]: https://github.com/quanduongduc/iot-data-tracking/network/members
[stars-shield]: https://img.shields.io/github/stars/othneildrew/Best-README-Template.svg?style=for-the-badge
[stars-url]: https://github.com/quanduongduc/iot-data-tracking/stargazers
[issues-shield]: https://img.shields.io/github/issues/othneildrew/Best-README-Template.svg?style=for-the-badge
[issues-url]: https://github.com/quanduongduc/iot-data-tracking/issues
[linkedin-shield]: https://img.shields.io/badge/-LinkedIn-black.svg?style=for-the-badge&logo=linkedin&colorB=555
[linkedin-url]: https://linkedin.com
