import re
from framework.run_command import *


def pre_settings():
    # update apt
    r.exec('sudo apt-get update')
    # disable automatic screen blanking
    r.exec('gsettings set org.gnome.desktop.session idle-delay 0')
    # create an empty template named 'new.sh'
    r.exec('touch ~/Templates/new.sh')
    r.exec('chmod 775 ~/Templates/new.sh')
    # install openssh server
    r.exec('sudo apt install openssh-server -y')
    # modify the ssh config to allow root login
    r.exec("sudo sed -i 's/^#PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config")
    r.exec('sudo systemctl restart sshd')
    # install python dev env
    r.exec('sudo apt-get install build-essential python3-dev python3-pip python-is-python3 -y')
    r.exec('sudo pip install --no-cache-dir psplpy')
    # install some other pieces of software
    # xclip for clip string to clipboard
    r.exec('sudo apt-get install xclip expect -y')
    # change the text size by resolution
    xrandr_info = r.capture("xrandr")
    match = re.search(r'current\s+(\d+)\s+x\s+(\d+)', xrandr_info)
    width, height = (int(match.group(1)), int(match.group(2))) if match else (0, 0)
    text_scaling = 1
    if width > 1920 or height > 1080:
        text_scaling = 1.25
    r.exec(f'gsettings set org.gnome.desktop.interface text-scaling-factor {text_scaling}')
    # show hidden files
    r.exec('gsettings set org.gtk.Settings.FileChooser show-hidden true')
    # add my scripts to path and make them executable
    scripts_dir = project_dir / "scripts"
    content = f'export PATH="$PATH:{scripts_dir}"'
    r.exec(f"echo '{content}' >> ~/.bashrc")
    r.exec(f'chmod +x {scripts_dir}/*')
    # create a /swapfile equals with the memory's size and mount it to enable hibernate
    memory_gb = r.capture("free -h | grep 'Mem:' | awk '{print $2}'")[:-3]
    r.exec(f'sudo {scripts_dir}/chswap {memory_gb}')
    has_mounted_swapfile = r.capture("cat /etc/fstab | grep '/swapfile'", ignore_error=True)
    if not has_mounted_swapfile:
        r.exec("echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab")
    # set 'sudo' not need password
    r.exec(f"echo 'ALL ALL = (ALL) NOPASSWD: ALL' | sudo tee -a /etc/sudoers")
    # adding file server's address to host
    r.input('file_server_address', 'File Server Address:\n')
    append_hosts(r.vars.file_server_address, 'fs')
    # password root and allow root to log into the desktop
    r.exec("echo 'root:root' | sudo chpasswd")
    old = '#  TimedLoginDelay = 10'
    r.replace('/etc/gdm3/custom.conf', old, f'{old}\\nAllowRoot=True')
    old = 'auth	required	pam_succeed_if.so user != root quiet_success'
    r.replace('/etc/pam.d/gdm-password', old, f'# {old}')


def post_settings():
    # uncomment WaylandEnable=false, enable X to make sure PIL.ImageGrab.grab(xdisplay=':0') work properly,
    # xdisplay='$DISPLAY' makes the remote development work properly
    # and this can make the gui in docker show correctly on host
    r.exec("sudo sed -i 's/#WaylandEnable=false/WaylandEnable=false/' /etc/gdm3/custom.conf")
    r.exec('sudo systemctl restart gdm3')


def append_hosts(ip: str, hosts: str) -> None:
    r.exec(f'echo "{ip} {hosts}" | sudo tee -a /etc/hosts')


def ip_configuration():
    netplan_name = '01-network-manager-all.yaml'
    netplan_path = Path('/etc/netplan') / netplan_name
    netplan_template = open(resources_dir / netplan_name).read()
    r.input('host_id', 'IP host ID:\n')
    ens_name = r.capture("ip link show | grep -oE 'ens[0-9]+'")  # 查找Ethernet设备名
    ens_name = ens_name.strip()
    netplan_content = netplan_template.format(ens_name=ens_name, host_ID=r.vars.host_id)
    command = f'echo "{netplan_content}" > {netplan_path}'
    r.exec(f"sudo bash -c '{command}'")  # 写入文件
    r.exec('sudo systemctl start systemd-networkd')
    r.exec('sudo netplan apply')


def set_proxy():
    r.exec("gsettings set org.gnome.system.proxy mode 'manual'")
    r.exec("gsettings set org.gnome.system.proxy.http host '127.0.0.1'")
    r.exec("gsettings set org.gnome.system.proxy.http port 7890")
    r.exec("gsettings set org.gnome.system.proxy.https host '127.0.0.1'")
    r.exec("gsettings set org.gnome.system.proxy.https port 7890")
    r.exec("gsettings set org.gnome.system.proxy mode 'none'")


def install_anaconda(installation_dir=Path('~/anaconda3')):
    anaconda_sh = 'Anaconda3-2023.09-0-Linux-x86_64.sh'
    save_path = f'/tmp/{anaconda_sh}'
    r.exec(f'curl -o {save_path} http://fs/files/softwares/{anaconda_sh}')
    # install
    r.exec(f'bash {save_path} -b -p {installation_dir} && '
           f'eval "$({installation_dir}/bin/conda shell.bash hook)" && '
           'conda init && '
           # set conda’s base environment not be activated on startup
           'conda config --set auto_activate_base false')
    # remove installation package
    r.exec(f'rm {save_path}')


def install_docker(version: str = '25.0.5'):
    # Add Docker's official GPG key
    r.exec('sudo apt-get install ca-certificates curl -y')
    r.exec('sudo install -m 0755 -d /etc/apt/keyrings')
    r.exec('sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc')
    r.exec('sudo chmod a+r /etc/apt/keyrings/docker.asc')
    # Add the repository to Apt sources
    r.exec('echo deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] '
           'https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | '
           'sudo tee /etc/apt/sources.list.d/docker.list > /dev/null')
    r.exec('sudo apt-get update')

    # Install the Docker packages
    if version:
        # List the available versions
        version_list = r.capture("apt-cache madison docker-ce | awk '{ print $3 }'").split('\n')
        version_string = ''
        for v in version_list:
            if version in v:
                version_string = v
        # set version env
        r.exec(f'VERSION_STRING={version_string} && '
               'sudo apt-get install docker-ce=$VERSION_STRING docker-ce-cli=$VERSION_STRING containerd.io '
               'docker-buildx-plugin docker-compose-plugin -y')
    else:
        # Install latest version
        r.exec('sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin')

    # Create the docker group
    r.exec('sudo groupadd docker', ignore_error=True)
    # Add your user to the docker group
    r.exec('sudo usermod -aG docker $USER')

    # setting the daemon.json
    r.exec(f'sudo cp {resources_dir / "daemon.json"} /etc/docker/daemon.json')

    # On Debian and Ubuntu, the Docker service starts on boot by default. for other distros, run the following commands
    r.exec('sudo systemctl enable docker.service')
    r.exec('sudo systemctl enable containerd.service')

    # check the versions of these binaries by running the following commands
    r.exec('sudo docker compose version')
    r.exec('sudo docker --version')
    r.exec('sudo docker version')


def install_docker_desktop():
    docker_desktop_deb = 'docker-desktop-4.27.1-amd64.deb'
    # Install docker desktop
    save_path = f'/tmp/{docker_desktop_deb}'
    r.exec(f'curl -o {save_path} http://fs/files/softwares/{docker_desktop_deb}')
    r.exec(f'sudo apt-get install {save_path} -y')
    # open Docker Desktop
    r.exec('systemctl --user start docker-desktop')
    # enable Docker Desktop to start on sign in
    r.exec('systemctl --user enable docker-desktop')
    # remove installation deb
    r.exec(f'rm {save_path}')


def login_docker():
    # You can initialize pass by using a gpg key. To generate a gpg key, run
    name = 'a'
    email = f'{name}@example.com'
    r.exec('echo "Key-Type: RSA" > keyparams && '
           'echo "Key-Length: 3072" >> keyparams && '
           f'echo "Name-Real: {name}" >> keyparams && '
           f'echo "Name-Email: {email}" >> keyparams && '
           'echo "Expire-Date: 2y" >> keyparams && '
           'gpg --batch --pinentry-mode loopback --passphrase "" --generate-key keyparams')
    output = r.capture(f'gpg --list-secret-keys {email}')
    match = re.search(rf'sec.*?\n(.*?)\nuid.*?{name} <{email}>', output)
    key = match.group(1).strip() if match else ''
    # To initialize pass, run the following command using the public key generated from the previous command
    r.exec(f'pass init {key}')

    # Login
    r.exec('echo "mu@Qyt^MiU56Gw#" | docker login -u wantodie --password-stdin')


def install_docker_registry():
    r.exec('mkdir ~/certs')
    r.exec('sudo apt-get install openssl')
    r.input('docker_registry_host_ID', 'Docker Registry host ID:\n')
    r.exec('openssl req -newkey rsa:4096 -nodes -sha256 -keyout ~/certs/domain.key -x509 -days 365 '
           f'-out ~/certs/domain.crt '
           f'-subj "/C=US/ST=New York/L=New York City/O=MyOrg/OU=MyUnit/CN=192.168.227.{r.vars.docker_registry_host_ID}" '
           f'-addext "subjectAltName = IP:192.168.227.{r.vars.docker_registry_host_ID}"')
    r.exec('docker run -d '
           '--restart=always '
           '--name registry '
           '-v ~/registry:/var/lib/registry '
           '-v ~/certs:/certs '
           '-e REGISTRY_HTTP_ADDR=0.0.0.0:443 '
           '-e REGISTRY_HTTP_TLS_CERTIFICATE=/certs/domain.crt '
           '-e REGISTRY_HTTP_TLS_KEY=/certs/domain.key '
           '-p 443:443 '
           'registry:2')


def add_registry_certificate_to_trusted():
    r.exec('sudo apt install sshpass')
    r.input('docker_registry_host_username', 'Docker Registry host username:\n')
    r.input('docker_registry_host_passwd', 'Docker Registry host password:\n')
    r.input('docker_registry_host_ID', 'Docker Registry host ID:\n')
    r.exec(f'sudo mkdir -p /etc/docker/certs.d/192.168.227.{r.vars.docker_registry_host_ID}:5000')
    r.exec(f'sudo sshpass -p "{r.vars.docker_registry_host_passwd}" scp -o StrictHostKeyChecking=no '
           f'{r.vars.docker_registry_host_username}@192.168.227.{r.vars.docker_registry_host_ID}:'
           f'~/certs/domain.crt /etc/docker/certs.d/192.168.227.{r.vars.docker_registry_host_ID}:5000/ca.crt')
    r.exec('sudo systemctl restart docker')


def install_pycharm():
    save_path = remote.get_file('software/pycharm-professional-2023.3.3.tar.gz')
    r.exec(f'tar -xvf {save_path} -C ~ > /dev/null')


def install_chrome():
    save_path = remote.get_file('software/google-chrome-stable_current_amd64.deb')
    r.exec(f'sudo dpkg -i {save_path}')


def install_wps():
    save_path = remote.get_file('software/wps')
    r.exec(f'sudo dpkg -i {save_path}')
    # this operation will resolve an internal error occurred after startup
    wps_cloud_dir = r.capture('find . -type d | grep -i "WPSCloudSvr"')
    r.exec(f'rm -r {wps_cloud_dir}')
    # resolve "Some formula symbols might not be displayed correctly due to missing fonts Symbol" issue
    save_path = remote.get_file('wps-fonts.zip')
    font_dir = '/usr/share/fonts/truetype/msttcorefonts/.'
    r.exec('sudo mkdir -p {font_dir}')
    r.exec(f'sudo unzip {save_path} -d {font_dir}')
    # refresh system font cache
    r.exec('sudo fc-cache -fv')


def install_wechat():
    r.exec('sudo apt update')
    r.exec(f'sudo apt install flatpak -y')
    r.exec('sudo flatpak remote-add --if-not-exists --system flathub https://flathub.org/repo/flathub.flatpakrepo')
    r.exec('flatpak install com.tencent.WeChat.flatpak -y')


def install_qq():
    save_path = remote.get_file('software/QQ_3.2.7_240422_amd64_01.deb')
    r.exec(f'sudo dpkg -i {save_path}')


def install_vmware_workstation():
    vmware_key = "vmware_key"
    pw = "1"
    # get essential files
    vmware_host_modules_path = remote.get_file('software/vmware-host-modules.tar.xz')
    r.exec(f'sudo tar -xvf {vmware_host_modules_path} -C {vmware_host_modules_path.parent}')
    vmware_path = remote.get_file('software/VMware-Workstation-Full-16.2.5-20904516.x86_64.bundle')
    # install vmware workstation
    r.exec(f'sudo chmod +x {vmware_path}')
    r.exec(f'sudo {vmware_path}')
    # install essential packages to compile vmmon and vmnet
    r.exec('sudo apt update')
    r.exec('sudo apt install build-essential gcc-12 linux-headers-"$(uname -r)" expect -y')
    # change the ownership of repository and compile
    r.exec(f'sudo chown -R --no-dereference $USER:$USER {vmware_host_modules_path.parent}')
    r.exec(f'cd {vmware_host_modules_path.parent / Path(vmware_host_modules_path.stem).stem} && '
           'sudo git checkout workstation-16.2.5 && '
           'sudo make && '
           'sudo make install && '
           # I have no idea but essential, otherwise "Could not open /dev/vmmon: No such file or directory" will occur
           f'sudo openssl req -new.sh -x509 -newkey rsa:2048 -keyout {vmware_key}.priv '
           f'-outform DER -out {vmware_key}.der -nodes -days 36500 -subj "/CN=VMware/" && '
           f'sudo /usr/src/linux-headers-"$(uname -r)"/scripts/sign-file sha256 ./{vmware_key}.priv ./{vmware_key}.der "$(modinfo -n vmmon)" && '
           f'sudo /usr/src/linux-headers-"$(uname -r)"/scripts/sign-file sha256 ./{vmware_key}.priv ./{vmware_key}.der "$(modinfo -n vmnet)" && '
           fr'''expect << EOF
spawn sudo mokutil --import {vmware_key}.der 
expect "password:"
send "{pw}\r"
EOF''')
    r.exec(f'echo "Password is: {pw}"')
    r.exec("echo \"Now it's time for reboot, remember the password. You will get a blue screen after reboot "
           "choose 'Enroll MOK' -> 'Continue' -> 'Yes' -> 'enter password' -> 'OK' or 'REBOOT' \"")
