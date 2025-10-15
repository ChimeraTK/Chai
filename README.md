# Chai

**Chai** (short for Console Hardware Interface) is a terminal user interface (TUI) for monitoring and changing hardware device register content. Chai provides an interface for register-based devices and aims to be a more accessible alternative to the Qt-based QtHardMon by eliminating the need for X-forwarding.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

## Features

- Monitor and modify hardware device register content
- Terminal User Interface (TUI) accessible via SSH
- Supports mouse and keyboard interactions
- View device status, register contents, and properties
- Read and write register values
- Auto-updating at 1Hz, 30Hz and 100Hz to mimic original QtHardMon
- Graphical display of value history

## Installation

### Prerequisites

- Python 3.8 or higher
- [Textual](https://github.com/Textualize/textual) library
- [ChimeraTK-DeviceAccess-PythonBindings](https://github.com/ChimeraTK/DeviceAccess-PythonBindings)

### Instructions

1. Ensure you have Python 3.8 or higher installed. You can check your Python version with:

    ```sh
    python3 --version
    ```

2. Install the required textual library:

    ```sh
    pip install textual
    ```

3. Chai will be available as a Debian package in the [DOOCS Debian repository](https://xwiki.desy.de/xwiki/bin/view/DOOCS/Documentation/DOOCS%20Installation%20Manual/) soon. Once available, you can install it using:

    ```sh
    sudo apt-get install chai
    ```

## Usage

To start using Chai, simply run the `chai.py` script in your console:

```sh
python3 chai.py
```

Once the TUI is open, you can:

- Load a `.dmap` file containing information about aliases of mapped devices and their registers.
- View device statuses and the contents and properties of each register.
- Read and write values to registers.
- Enable auto-updating to refresh data at 1Hz or 100Hz.

## Issues with Putty

If you are experiencing unicode character ir color issues PuTTY, it might be solved by using another font.
[Nerdfonts](https://www.nerdfonts.com/font-downloads) proved to solve the character issue.
Better readability of the colors and a closer match to the Ubuntu experience can be achieved with [this guide](https://github.com/jblaine/solarized-and-modern-putty) to change PuTTY's default setting.

## Contributing

We welcome contributions from the community! If you wish to contribute, please follow these steps:

1. Fork the repository on GitHub.
2. Create a new branch with a descriptive name.
3. Make your changes and commit them with clear and concise messages.
4. Push your changes to your fork.
5. Create a pull request detailing your changes.

## License

Chai is licensed under the LGPL-3.0 License. See the [LICENSE](LICENSE) file for more details.

## Contact

This project is maintained by the MSK Software Group at DESY, Germany. If you have any questions or feedback, please open an issue on GitHub or submit a pull request.

---

We hope you find Chai useful and look forward to your contributions!
