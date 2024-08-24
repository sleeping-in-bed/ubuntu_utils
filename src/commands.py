import math
import shutil
from framework.instances import *


def append_hosts(ip: str, host: str) -> None:
    hosts_path = Path('/etc/hosts')
    new_host = f'{ip} {host}'
    hosts_contents = hosts_path.read_text()
    if new_host not in hosts_contents:
        hosts_path.write_text(hosts_contents + f'\n{new_host}')


def check_and_modify_the_lang():
    if not r.capture('echo $LANG', no_check=True) == 'en_US.UTF-8':
        r.exec('sudo update-locale LANG=en_US.UTF-8', no_check=True)
        r.exec('sudo update-locale', no_check=True)
        # change the standard dirs name
        # log out the desktop environment to apply the changes
        r.exec('gnome-session-quit --logout --no-prompt', no_check=True)
        # then select change the standard dirs name


def install_python_libs():
    r.exec('sudo pip install --no-cache-dir psplpy pyautogui pynput opencv-python docker')
    r.exec('sudo apt-get install -y python3-tk python3-dev')    # to use the pyautogui


def general_upgrade():
    # update apt & upgrade software and disable software update notifications & auto install drivers
    r.exec('sudo apt update')
    r.exec('sudo apt upgrade -y')
    r.exec('gsettings set com.ubuntu.update-notifier no-show-notifications true')
    r.exec('sudo ubuntu-drivers install')
    # install language supports and add pinyin input sources
    r.exec('sudo apt install -y $(check-language-support)')
    input_source = "[('xkb', 'us'), ('ibus', 'libpinyin')]"
    r.exec(f'gsettings set org.gnome.desktop.input-sources sources "{input_source}"')


def pre_settings():
    r.exec('sudo apt update')
    # set do nothing when close laptop lid
    r.replace('/etc/systemd/logind.conf', '#HandleLidSwitch=suspend', 'HandleLidSwitch=ignore')
    # disable automatic screen blanking
    r.exec('gsettings set org.gnome.desktop.session idle-delay 0')
    # create an empty template named 'new'
    r.exec('touch ~/Templates/new')
    r.exec('chmod 775 ~/Templates/new')
    # install openssh server & modify the ssh config to allow root login
    r.exec('sudo apt install openssh-server -y')
    r.exec("sudo sed -i 's/^#PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config")
    r.exec('sudo systemctl restart sshd')
    # install python dev env
    r.exec('sudo apt-get install build-essential python3-dev python3-pip python-is-python3 -y')
    install_python_libs()
    # install some other software
    # baobab is the disk usage analyzer, xclip for clipping string to clipboard, expect for simulating input
    r.exec('sudo apt-get install baobab xclip expect -y')
    # change the text size by the resolution
    xrandr_info = r.capture("xrandr", no_check=True).stdout
    match = re.search(r'current\s+(\d+)\s+x\s+(\d+)', xrandr_info)
    width, height = (int(match.group(1)), int(match.group(2))) if match else (0, 0)
    print(width, height)
    text_scaling = 1
    if width > 1920 or height > 1080:
        text_scaling = 1.25
    r.exec(f'gsettings set org.gnome.desktop.interface text-scaling-factor {text_scaling}')
    # show hidden files
    r.exec('gsettings set org.gtk.Settings.FileChooser show-hidden true')
    # add my scripts to path and make them executable
    content = f'export PATH="$PATH:{scripts_dir}"'
    r.exec(f"echo '{content}' >> ~/.bashrc")
    r.exec(f'chmod +x {scripts_dir}/*')
    # create a /swapfile equals with the memory's size and mount it to enable hibernate
    memory_gb = r.capture("free -h | grep 'Mem:' | awk '{print $2}'", no_check=True).stdout[:-3]
    r.chdir(scripts_dir)
    r.exec(f'sudo ./chswap {math.ceil(1.05 * float(memory_gb))}')
    has_mounted_swapfile = r.capture("cat /etc/fstab | grep '/swapfile'", ignore_error=True).stdout
    if not has_mounted_swapfile:
        r.exec("echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab")
    # set 'sudo' not need password
    r.exec(f"echo 'ALL ALL = (ALL) NOPASSWD: ALL' | sudo tee -a /etc/sudoers")
    # adding file server's address to host
    append_hosts(r.vars['file_server_address'], 'fs')
    # password root and allow root to log into the desktop
    r.exec("echo 'root:root' | sudo chpasswd")
    old = '#  TimedLoginDelay = 10'
    r.replace('/etc/gdm3/custom.conf', old, f'{old}\\nAllowRoot=True')
    old = 'auth	required	pam_succeed_if.so user != root quiet_success'
    r.replace('/etc/pam.d/gdm-password', old, f'# {old}')
    # install flatpak
    r.exec('sudo apt install -y flatpak')
    r.exec('sudo flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo')


def post_settings():
    # clear the cache and trash files
    r.chdir(scripts_dir)
    r.exec(f'sudo ./free-space')
    # uncomment WaylandEnable=false, enable X to make sure PIL.ImageGrab.grab(xdisplay=':0') work properly,
    # xdisplay='$DISPLAY' makes the remote development work properly
    # and this can make the gui in docker show correctly on host
    r.exec("sudo sed -i 's/#WaylandEnable=false/WaylandEnable=false/' /etc/gdm3/custom.conf")
    r.exec('sudo systemctl restart gdm3')


def ip_configuration():
    netplan_name = '01-network-manager-all.yaml'
    netplan_path = Path('/etc/netplan') / netplan_name
    netplan_template = open(resources_dir / netplan_name).read()
    ens_name = r.capture("ip link show | grep -oE 'ens[0-9]+'").stdout  # 查找Ethernet设备名
    ens_name = ens_name.strip()
    netplan_content = netplan_template.format(ens_name=ens_name, host_ID=r.vars['host_addr'])
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
    r.exec('sudo apt update')
    # Add Docker's official GPG key
    r.exec('sudo apt-get install ca-certificates curl -y')
    r.exec('sudo install -m 0755 -d /etc/apt/keyrings')
    r.exec('sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc')
    r.exec('sudo chmod a+r /etc/apt/keyrings/docker.asc')
    # Add the repository to Apt sources
    r.exec('echo \
"deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
$(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
sudo tee /etc/apt/sources.list.d/docker.list > /dev/null')
    r.exec('sudo apt-get update')

    # Install the Docker packages
    if version:
        # List the available versions
        version_list = r.capture("apt-cache madison docker-ce | awk '{ print $3 }'",
                                 no_check=True).stdout.split('\n')
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
        r.exec(
            'sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin -y')

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
    # Install docker desktop
    save_path = remote.get_file('software/docker-desktop-4.27.1-amd64.deb')
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
    output = r.capture(f'gpg --list-secret-keys {email}').stdout
    match = re.search(rf'sec.*?\n(.*?)\nuid.*?{name} <{email}>', output)
    key = match.group(1).strip() if match else ''
    # To initialize pass, run the following command using the public key generated from the previous command
    r.exec(f'pass init {key}')

    # Login
    r.exec('echo "mu@Qyt^MiU56Gw#" | docker login -u wantodie --password-stdin')


def install_docker_registry():
    r.exec('mkdir ~/certs')
    r.exec('sudo apt-get install openssl')
    r.exec('openssl req -newkey rsa:4096 -nodes -sha256 -keyout ~/certs/domain.key -x509 -days 365 '
           f'-out ~/certs/domain.crt '
           f'-subj "/C=US/ST=New York/L=New York City/O=MyOrg/OU=MyUnit/CN={r.vars["network_addr"]}.{r.vars["host_addr"]}" '
           f'-addext "subjectAltName = IP:{r.vars["network_addr"]}.{r.vars["host_addr"]}"')
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
    r.exec(f'sudo mkdir -p /etc/docker/certs.d/{r.vars["network_addr"]}.{r.vars["host_addr"]}:5000')
    r.exec(f'sudo sshpass -p "{r.vars["password"]}" scp -o StrictHostKeyChecking=no '
           f'{r.vars["username"]}@192.168.227.{r.vars["host_addr"]}:'
           f'~/certs/domain.crt /etc/docker/certs.d/{r.vars["network_addr"]}.{r.vars["host_addr"]}:5000/ca.crt')
    r.exec('sudo systemctl restart docker')


def install_pycharm(remote_version: bool = True, version: str = '2023.3.3'):
    if remote_version:
        save_path = remote.get_file('docker/files/cache.tar.xz')
        bin_dir = f'{r.home}/.cache/JetBrains/RemoteDev/dist/29c4955410b2e_pycharm-professional-{version}/bin'
    else:
        save_path = remote.get_file('software/pycharm-professional-2023.3.3.tar.gz')
        bin_dir = f'{r.home}/pycharm-professional-{version}/bin'
    r.exec(f'tar -xf {save_path} -C ~')

    r.exec(f'sudo ln -s {bin_dir}/pycharm.sh /usr/local/bin/pycharm')
    r.chdir(scripts_dir)
    r.exec(f'./shortcut {bin_dir}/pycharm.sh -n pycharm -i {bin_dir}/pycharm.png -t false')


def install_chrome():
    save_path = remote.get_file('software/google-chrome-stable_current_amd64.deb')
    r.exec(f'sudo dpkg -i {save_path}')


def install_wps():
    save_path = remote.get_file('software/wps-office_11.1.0.11719.XA_amd64.deb')
    r.exec(f'sudo dpkg -i {save_path}')
    # this operation will resolve an internal error occurred after startup
    wps_cloud_dir = r.capture('sudo find /opt -name "wpscloudsvr"').stdout
    r.exec(f'sudo rm -f {wps_cloud_dir}')
    # resolve "Some formula symbols might not be displayed correctly due to missing fonts Symbol" issue
    save_path = remote.get_file('software/wps-fonts.zip')
    font_dir = '/usr/share/fonts/truetype/msttcorefonts'
    r.exec(f'sudo mkdir -p {font_dir}')
    r.exec(f'sudo unzip {save_path} -d {font_dir}')
    # refresh system font cache
    r.exec('sudo fc-cache -fv')


def install_wechat():
    r.exec('flatpak install -y com.tencent.WeChat')


def install_qq():
    save_path = remote.get_file('software/QQ_3.2.7_240422_amd64_01.deb')
    r.exec(f'sudo dpkg -i {save_path}')


def install_vmware_workstation():
    vmware_key = "vmware_key"
    # get essential files
    vmware_host_modules_path = remote.get_file('software/vmware-host-modules.tar.xz')
    r.exec(f'sudo tar -xvf {vmware_host_modules_path} -C {vmware_host_modules_path.parent}')
    vmware_path = remote.get_file('software/VMware-Workstation-Full-16.2.5-20904516.x86_64.bundle')
    # install vmware workstation
    r.exec(f'sudo chmod +x {vmware_path}')
    r.exec(f'sudo {vmware_path}')
    # install essential packages to compile vmmon and vmnet
    r.exec('sudo apt update && sudo apt install build-essential gcc-12 linux-headers-"$(uname -r)" -y')
    # change the ownership of repository and compile
    r.exec(f'sudo chown -R --no-dereference $USER:$USER {vmware_host_modules_path.parent}')
    r.exec(f'cd {vmware_host_modules_path.parent / Path(vmware_host_modules_path.stem).stem} && '
           'sudo git checkout workstation-16.2.5 && '
           'sudo make && '
           'sudo make install && '
           # I have no idea but essential, otherwise "Could not open /dev/vmmon: No such file or directory" will occur
           f'sudo openssl req -new -x509 -newkey rsa:2048 -keyout {vmware_key}.priv '
           f'-outform DER -out {vmware_key}.der -nodes -days 36500 -subj "/CN=VMware/" && '
           f'sudo /usr/src/linux-headers-`uname -r`/scripts/sign-file sha256 ./{vmware_key}.priv ./{vmware_key}.der "$(modinfo -n vmmon)" && '
           f'sudo /usr/src/linux-headers-`uname -r`/scripts/sign-file sha256 ./{vmware_key}.priv ./{vmware_key}.der "$(modinfo -n vmnet)" && '
           f'sudo mokutil --import {vmware_key}.der')
    r.exec("echo \"Now it's time for reboot, remember the password. You will get a blue screen after reboot "
           "choose 'Enroll MOK' -> 'Continue' -> 'Yes' -> 'enter password' -> 'OK' or 'REBOOT' \"")


def install_nvidia_container_toolkit():
    r.exec("curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
            && curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
            sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
            sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list")
    r.exec('sudo apt update && sudo apt install -y nvidia-container-toolkit')
    r.exec('sudo nvidia-ctk runtime configure --runtime=docker')
    r.exec('sudo systemctl restart docker')


def install_mission_center():
    app_name = 'io.missioncenter.MissionCenter'
    r.exec(f'flatpak install -y {app_name}')
    shutil.copy2(f'/var/lib/flatpak/app/{app_name}/current/active/files/share/applications/{app_name}.desktop',
                 f'/usr/share/applications/{app_name}.desktop')


def install_sougoupinyin():
    save_path = remote.get_file('software/sogoupinyin_4.2.1.145_amd64.deb')
    r.exec(f'sudo apt update && sudo apt install -y fcitx')
    # set the fcitx starting on boot
    r.exec(f'sudo cp /usr/share/applications/fcitx.desktop /etc/xdg/autostart/')
    r.exec(f'sudo apt install -y libqt5qml5 libqt5quick5 libqt5quickwidgets5 qml-module-qtquick2 libgsettings-qt1')
    r.exec(f'sudo dpkg -i {save_path}')
    r.exec(f"gsettings set org.gnome.desktop.input-sources sources \"[('xkb', 'fcitx')]\"")


def install_vlc():
    r.exec(f'sudo apt install -y vlc')


def common_procedure():
    try:
        pre_settings()
        install_docker()
        install_pycharm()
        install_chrome()
        if not is_vmware():
            install_nvidia_container_toolkit()
            set_proxy()
            install_vmware_workstation()
            install_wps()
            install_mission_center()
            install_vlc()
        install_sougoupinyin()
        post_settings()
    finally:
        close_all()
