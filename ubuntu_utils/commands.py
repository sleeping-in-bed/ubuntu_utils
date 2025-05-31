import math
import re
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
import configs
from framework.process import RootProcess
from framework.remote import Remote
from framework.settings import Settings

r: RootProcess = RootProcess()
remote: Remote = Remote()


def append_hosts(ip: str, host: str) -> None:
    hosts_path = Path("/etc/hosts")
    new_host = f"{ip} {host}"
    hosts_contents = hosts_path.read_text()
    if new_host not in hosts_contents:
        hosts_path.write_text(hosts_contents + f"\n{new_host}")


def check_and_modify_the_lang():
    """Be used in the chinese ubuntu, convert the standard dirname to english"""
    if r.capture("echo $LANG", no_check=True) != "en_US.UTF-8":
        r.exec("sudo update-locale LANG=en_US.UTF-8", no_check=True)
        r.exec("sudo update-locale", no_check=True)
        # change the standard dirs name
        # log out the desktop environment to apply the changes
        r.exec("gnome-session-quit --logout --no-prompt", no_check=True)
        # then select change the standard dirs name


def apt_offline_install():
    r.exec("sudo apt update")
    r.exec(
        f"sudo apt install -y {Settings.resources_dir / 'apt-offline_1.8.6-1_all.deb'}"
    )
    file = None
    for file in remote.get_file_paths("apt_offline"):
        file = remote.get_file(f"apt_offline/{file}")
    if file:
        r.exec(f'sudo apt-offline install "{file.parent}"')


def install_python():
    # install python
    r.exec(
        "sudo apt-get install -y build-essential python3-dev python3-pip python-is-python3"
    )
    r.exec("sudo apt-get install -y python3-tk")  # to use the pyautogui
    # install pyenv
    r.exec(
        "curl -fsSL https://pyenv.run | bash",
        ignore_error=[
            re.compile(
                r"WARNING: Can not proceed with installation. Kindly remove the '.*' directory first."
            )
        ],
    )
    r.exec("""echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc &&
echo '[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc &&
echo 'eval "$(pyenv init - bash)"' >> ~/.bashrc &&
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.profile &&
echo '[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.profile &&
echo 'eval "$(pyenv init - bash)"' >> ~/.profile
""")
    # install uv
    # add PATH before uv
    r.exec(
        r"""grep -Fxq 'export PATH="$HOME/.local/bin:$PATH"' ~/.bashrc || echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc"""
    )
    # install uv
    r.exec(r"""curl -LsSf https://astral.sh/uv/install.sh | sh &&
bash -c "source $HOME/.local/bin/env &&
uv tool install tox --with tox-uv" &&
grep -Fxq 'eval "$(uv generate-shell-completion bash)"' ~/.bashrc || echo 'eval "$(uv generate-shell-completion bash)"' >> ~/.bashrc &&
grep -Fxq 'eval "$(uvx --generate-shell-completion bash)"' ~/.bashrc || echo 'eval "$(uvx --generate-shell-completion bash)"' >> ~/.bashrc
""")
    # install nvm
    r.exec(r"""curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash &&
export NVM_DIR="$HOME/.nvm" &&
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm &&
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion &&
nvm install --lts""")


def pre_settings():
    # show system info
    r.exec("uname -r")
    r.exec("lsb_release -d")
    apt_offline_install()
    r.exec("sudo ubuntu-drivers install")
    if r.has_gui:
        # disable software update notifications & auto install drivers
        r.exec("gsettings set com.ubuntu.update-notifier no-show-notifications true")
        # install language supports and add pinyin input sources
        r.exec("sudo apt install -y $(check-language-support)")
        input_source = "[('xkb', 'us'), ('ibus', 'libpinyin')]"
        r.exec(
            f'gsettings set org.gnome.desktop.input-sources sources "{input_source}"'
        )
        # set do nothing when close laptop lid
        r.replace(
            "/etc/systemd/logind.conf",
            "#HandleLidSwitch=suspend",
            "HandleLidSwitch=ignore",
        )
        # disable automatic screen blanking
        r.exec("gsettings set org.gnome.desktop.session idle-delay 0")
        # create an empty template named 'new'
        r.exec("touch ~/Templates/new")
        r.exec("chmod 775 ~/Templates/new")
        # change the text size by the resolution
        r.chdir(Settings.scripts_dir)
        r.exec("./chtext")
        # show hidden files
        r.exec("gsettings set org.gtk.Settings.FileChooser show-hidden true")
        # install some software, baobab is the disk usage analyzer
        r.exec("sudo apt-get -y install baobab")
    # install openssh server & modify the ssh config to allow root login
    r.exec("sudo apt install -y openssh-server")
    r.exec(
        "sudo sed -i 's/^#PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config"
    )
    r.exec("sudo systemctl restart ssh")
    # install some other software
    # xclip for clipping string to clipboard, expect for simulating input
    r.exec("sudo apt-get -y install xclip expect curl git")
    # install python dev environment
    install_python()
    # add my scripts to path and make them executable
    content = f'export PATH="$PATH:{Settings.scripts_dir}"'
    r.exec(f"echo '{content}' >> ~/.bashrc")
    r.exec(f"sudo chmod +x {Settings.scripts_dir}/*")
    # create a /swapfile equals with the memory's size and mount it to enable hibernate
    memory_gb = r.capture(
        "free -h | grep 'Mem:' | awk '{print $2}'", no_check=True
    ).stdout[:-3]
    r.chdir(Settings.scripts_dir)
    r.exec(f"sudo ./chswap {math.ceil(1.05 * float(memory_gb))}")
    has_mounted_swapfile = r.capture(
        "cat /etc/fstab | grep '/swapfile'", ignore_error=True
    ).stdout
    if not has_mounted_swapfile:
        r.exec("echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab")
    # set 'sudo' not need password
    r.exec("echo 'ALL ALL = (ALL) NOPASSWD: ALL' | sudo tee -a /etc/sudoers")
    # password root and allow root to log into the desktop
    root_password = configs.ROOT_PASSWORD or "root"
    r.exec(f"echo 'root:{root_password}' | sudo chpasswd")
    if r.has_gui:
        old = "#  TimedLoginDelay = 10"
        r.replace("/etc/gdm3/custom.conf", old, f"{old}\nAllowRoot=True")
        old = "auth	required	pam_succeed_if.so user != root quiet_success"
        r.replace("/etc/pam.d/gdm-password", old, f"# {old}")
    # install flatpak, make sure the system time is correct before installing
    r.exec("sudo apt install -y flatpak")
    r.exec(
        "sudo flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo"
    )
    # set git
    r.exec(f'''git config --global user.name "{configs.NAME}" &&
git config --global user.email "{configs.EMAIL}" &&
git config --global core.autocrlf input''')


def post_settings():
    # clear the cache and trash files
    r.chdir(Settings.scripts_dir)
    r.exec("sudo ./free-space")
    if r.has_gui:
        # uncomment WaylandEnable=false, enable X to make sure PIL.ImageGrab.grab(xdisplay=':0') work properly,
        # xdisplay='$DISPLAY' makes the remote development work properly
        # and this can make the gui in docker show correctly on host
        r.exec(
            "sudo sed -i 's/#WaylandEnable=false/WaylandEnable=false/' /etc/gdm3/custom.conf"
        )
        r.exec("sudo systemctl restart gdm3")


def ip_configuration():
    netplan_name = "01-network-manager-all.yaml"
    netplan_path = Path("/etc/netplan") / netplan_name
    netplan_template = (Settings.resources_dir / netplan_name).read_text(
        encoding="utf-8"
    )
    ens_name = r.capture(
        "ip link show | grep -oE 'ens[0-9]+'"
    ).stdout  # 查找Ethernet设备名
    ens_name = ens_name.strip()
    netplan_content = netplan_template.format(
        ens_name=ens_name,
        host_ip=configs.HOST_IP,
        gateway=configs.GATEWAY,
    )
    netplan_path.write_text(netplan_content, encoding="utf-8")
    r.exec("sudo systemctl start systemd-networkd")
    r.exec("sudo netplan apply")


def set_proxy():
    r.exec("""gsettings set org.gnome.system.proxy mode 'manual'
gsettings set org.gnome.system.proxy.http host '127.0.0.1'
gsettings set org.gnome.system.proxy.http port 7890
gsettings set org.gnome.system.proxy.https host '127.0.0.1'
gsettings set org.gnome.system.proxy.https port 7890
gsettings set org.gnome.system.proxy mode 'none'""")


def install_anaconda(installation_dir=Path("~/anaconda3")):
    save_path = remote.get_file("software/Anaconda3-2023.09-0-Linux-x86_64.sh")
    r.exec(
        f"bash {save_path} -b -p {installation_dir} && "
        f'eval "$({installation_dir}/bin/conda shell.bash hook)" && '
        "conda init && "
        # set conda’s base environment not be activated on startup
        "conda config --set auto_activate_base false"
    )
    # remove installation package
    r.exec(f"rm {save_path}")


def install_docker(version: str = ""):
    r.exec("sudo apt update")
    # Add Docker's official GPG key
    r.exec("""sudo apt-get install ca-certificates curl -y
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc""")
    # Add the repository to Apt sources
    r.exec(
        'echo \
"deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
$(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
sudo tee /etc/apt/sources.list.d/docker.list > /dev/null'
    )
    r.exec("sudo apt-get update")

    # Install the Docker packages
    if version:
        # List the available versions
        version_list = r.capture(
            "apt-cache madison docker-ce | awk '{ print $3 }'", no_check=True
        ).stdout.split("\n")
        version_string = ""
        for v in version_list:
            if version in v:
                version_string = v
        # set version env
        r.exec(
            f"VERSION_STRING={version_string} && "
            "sudo apt-get install docker-ce=$VERSION_STRING docker-ce-cli=$VERSION_STRING containerd.io "
            "docker-buildx-plugin docker-compose-plugin -y"
        )
    else:
        # Install the latest version
        r.exec(
            "sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin -y"
        )

    # create the docker group
    r.exec("sudo groupadd docker", ignore_error=True)
    # Add your user to the docker group
    r.exec("sudo usermod -aG docker $USER")

    # setting the daemon.json
    # r.exec(f'sudo cp {Settings.resources_dir / "daemon.json"} /etc/docker/daemon.json')

    # on Debian and Ubuntu, the Docker service starts on boot by default. for other distros, run the following commands
    r.exec("""sudo systemctl enable docker.service
sudo systemctl enable containerd.service""")

    # check the versions of these binaries by running the following commands
    r.exec("""sudo docker compose version
sudo docker --version
sudo docker version""")


def restore_docker_images():
    def decompress_file(file_path):
        r.chdir(Settings.scripts_dir)
        file = remote.get_file(file_path)
        r.exec(f'sudo ./xz-docker -d "{file}"')

    with ThreadPoolExecutor() as executor:
        file_paths = remote.get_file_paths("docker/images")
        executor.map(decompress_file, file_paths)


def install_docker_desktop():
    # Install docker desktop
    save_path = remote.get_file("software/docker-desktop-4.27.1-amd64.deb")
    r.exec(f"sudo apt-get install {save_path} -y")
    # open Docker Desktop
    r.exec("systemctl --user start docker-desktop")
    # enable Docker Desktop to start on sign in
    r.exec("systemctl --user enable docker-desktop")
    # remove installation deb
    r.exec(f"rm {save_path}")


def login_docker():
    # You can initialize pass by using a gpg key. To generate a gpg key, run
    r.exec(f"""echo "Key-Type: RSA" > keyparams &&
echo "Key-Length: 3072" >> keyparams &&
echo "Name-Real: {configs.NAME}" >> keyparams &&
echo "Name-Email: {configs.EMAIL}" >> keyparams &&
echo "Expire-Date: 2y" >> keyparams &&
gpg --batch --pinentry-mode loopback --passphrase "" --generate-key keyparams""")
    output = r.capture(f"gpg --list-secret-keys {configs.EMAIL}").stdout
    match = re.search(rf"sec.*?\n(.*?)\nuid.*?{configs.NAME} <{configs.EMAIL}>", output)
    key = match.group(1).strip() if match else ""
    # To initialize pass, run the following command using the public key generated from the previous command
    r.exec(f"pass init {key}")

    # Login
    r.exec(
        f'echo "{configs.DOCKERHUB_PASSWORD}" | docker login -u {configs.DOCKERHUB_NAME} --password-stdin'
    )


def install_docker_registry():
    r.exec("mkdir ~/certs")
    r.exec("sudo apt-get install openssl")
    r.exec(
        "openssl req -newkey rsa:4096 -nodes -sha256 -keyout ~/certs/domain.key -x509 -days 365 "
        f"-out ~/certs/domain.crt "
        f'-subj "/C=US/ST=New York/L=New York City/O=MyOrg/OU=MyUnit/CN={configs.HOST_IP}" '
        f'-addext "subjectAltName = IP:{configs.HOST_IP}"'
    )
    r.exec(
        "docker run -d "
        "--restart=always "
        "--name registry "
        "-v ~/registry:/var/lib/registry "
        "-v ~/certs:/certs "
        "-e REGISTRY_HTTP_ADDR=0.0.0.0:443 "
        "-e REGISTRY_HTTP_TLS_CERTIFICATE=/certs/domain.crt "
        "-e REGISTRY_HTTP_TLS_KEY=/certs/domain.key "
        "-p 443:443 "
        "registry:2"
    )


def add_registry_certificate_to_trusted():
    r.exec("sudo apt install sshpass")
    r.exec(f"sudo mkdir -p /etc/docker/certs.d/{configs.HOST_IP}:5000")
    r.exec(
        f'sudo sshpass -p "{configs.PASSWORD}" scp -o StrictHostKeyChecking=no '
        f"{configs.USERNAME}@{configs.HOST_IP}:"
        f"~/certs/domain.crt /etc/docker/certs.d/{configs.HOST_IP}:5000/ca.crt"
    )
    r.exec("sudo systemctl restart docker")


def install_pycharm(remote_version: bool = True, version: str = "2023.3.3"):
    if remote_version:
        save_path = remote.get_file("docker/files/cache.tar.xz")
        bin_dir = f"{r.home}/.cache/JetBrains/RemoteDev/dist/29c4955410b2e_pycharm-professional-{version}/bin"
    else:
        save_path = remote.get_file("software/pycharm-professional-2023.3.3.tar.gz")
        bin_dir = f"{r.home}/pycharm-professional-{version}/bin"
    r.exec(f"tar -xf {save_path} -C ~")

    r.exec(f"sudo ln -s {bin_dir}/pycharm.sh /usr/local/bin/pycharm")
    r.chdir(Settings.scripts_dir)
    r.exec(
        f"./shortcut {bin_dir}/pycharm.sh -n pycharm -i {bin_dir}/pycharm.png -t false"
    )


def install_chrome():
    save_path = remote.get_file("software/google-chrome-stable_current_amd64.deb")
    r.exec(f"sudo dpkg -i {save_path}")


def install_wps():
    save_path = remote.get_file("software/wps-office_11.1.0.11719.XA_amd64.deb")
    r.exec(f"sudo dpkg -i {save_path}")
    # this operation will resolve an internal error occurred after startup
    wps_cloud_dir = r.capture('sudo find /opt -name "wpscloudsvr"').stdout
    r.exec(f"sudo rm -f {wps_cloud_dir}")
    # resolve "Some formula symbols might not be displayed correctly due to missing fonts Symbol" issue
    save_path = remote.get_file("software/wps-fonts.zip")
    font_dir = "/usr/share/fonts/truetype/msttcorefonts"
    r.exec(f"sudo mkdir -p {font_dir}")
    r.exec(f"sudo unzip {save_path} -d {font_dir}")
    # refresh system font cache
    r.exec("sudo fc-cache -fv")


def install_wechat():
    r.exec("flatpak install -y com.tencent.WeChat")


def install_qq():
    save_path = remote.get_file("software/QQ_3.2.7_240422_amd64_01.deb")
    r.exec(f"sudo dpkg -i {save_path}")


def install_vmware_workstation():
    vmware_key = "vmware_key"
    # get essential files
    vmware_host_modules_path = remote.get_file("software/vmware-host-modules.tar.xz")
    r.exec(
        f"sudo tar -xvf {vmware_host_modules_path} -C {vmware_host_modules_path.parent}"
    )
    vmware_path = remote.get_file(
        "software/VMware-Workstation-Full-16.2.5-20904516.x86_64.bundle"
    )
    # install vmware workstation
    r.exec(f"sudo chmod +x {vmware_path}")
    r.exec(f"sudo {vmware_path}")
    # install essential packages to compile vmmon and vmnet
    r.exec(
        'sudo apt update && sudo apt install build-essential gcc-12 linux-headers-"$(uname -r)" -y'
    )
    # change the ownership of repository and compile
    r.exec(
        f"sudo chown -R --no-dereference $USER:$USER {vmware_host_modules_path.parent}"
    )
    r.exec(
        f"cd {vmware_host_modules_path.parent / Path(vmware_host_modules_path.stem).stem} && "
        "sudo git checkout workstation-16.2.5 && "
        "sudo make && "
        "sudo make install && "
        # I have no idea but essential, otherwise "Could not open /dev/vmmon: No such file or directory" will occur
        f"sudo openssl req -new -x509 -newkey rsa:2048 -keyout {vmware_key}.priv "
        f'-outform DER -out {vmware_key}.der -nodes -days 36500 -subj "/CN=VMware/" && '
        f'sudo /usr/src/linux-headers-`uname -r`/scripts/sign-file sha256 ./{vmware_key}.priv ./{vmware_key}.der "$(modinfo -n vmmon)" && '
        f'sudo /usr/src/linux-headers-`uname -r`/scripts/sign-file sha256 ./{vmware_key}.priv ./{vmware_key}.der "$(modinfo -n vmnet)" && '
        f"sudo mokutil --import {vmware_key}.der"
    )
    r.exec(
        "echo \"Now it's time for reboot, remember the password. You will get a blue screen after reboot "
        "choose 'Enroll MOK' -> 'Continue' -> 'Yes' -> 'enter password' -> 'OK' or 'REBOOT' \""
    )


def install_nvidia_container_toolkit():
    r.exec(
        "curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
            && curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
            sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
            sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list"
    )
    r.exec("sudo apt update && sudo apt install -y nvidia-container-toolkit")
    r.exec("sudo nvidia-ctk runtime configure --runtime=docker")
    r.exec("sudo systemctl restart docker")


def install_mission_center():
    app_name = "io.missioncenter.MissionCenter"
    r.exec(f"flatpak install -y {app_name}")
    shutil.copy2(
        f"/var/lib/flatpak/app/{app_name}/current/active/files/share/applications/{app_name}.desktop",
        f"/usr/share/applications/{app_name}.desktop",
    )


def install_sougoupinyin():
    save_path = remote.get_file("software/sogoupinyin_4.2.1.145_amd64.deb")
    r.exec("sudo apt update && sudo apt install -y fcitx")
    # set the fcitx starting on boot
    r.exec("sudo cp /usr/share/applications/fcitx.desktop /etc/xdg/autostart/")
    r.exec(
        "sudo apt install -y libqt5qml5 libqt5quick5 libqt5quickwidgets5 qml-module-qtquick2 libgsettings-qt1"
    )
    r.exec(f"sudo dpkg -i {save_path}")
    r.exec(
        "gsettings set org.gnome.desktop.input-sources sources \"[('xkb', 'fcitx')]\""
    )


def install_vlc():
    r.exec("sudo apt install -y vlc")


def install_kubernetes(version="1.32.0-1.1"):
    r.chdir(Settings.scripts_dir)
    r.exec("./chswap 0")

    r.exec("""cat << EOF | sudo tee /etc/modules-load.d/k8s.conf
overlay
br_netfilter
EOF""")
    r.exec("""sudo modprobe overlay
sudo modprobe br_netfilter""")
    r.exec("""cat << EOF | sudo tee /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-ip6tables = 1
net.bridge.bridge-nf-call-iptables = 1
net.ipv4.ip_forward = 1
EOF""")
    r.exec("sudo sysctl --system")

    r.exec("sudo apt install -y ipset ipvsadm")
    r.exec("""cat << EOF | sudo tee /etc/modules-load.d/ipvs.conf
ip_vs
ip_vs_rr
ip_vs_wrr
ip_vs_sh
nf_conntrack
EOF""")
    r.exec("""sudo modprobe -- ip_vs
sudo modprobe -- ip_vs_rr
sudo modprobe -- ip_vs_wrr
sudo modprobe -- ip_vs_sh
sudo modprobe -- nf_conntrack""")

    r.exec("containerd config default > /etc/containerd/config.toml")
    r.replace(
        "/etc/containerd/config.toml", "SystemdCgroup = false", "SystemdCgroup = true"
    )
    r.replace(
        "/etc/containerd/config.toml",
        re.compile(r"sandbox_image(.*?)\n"),
        'sandbox_image = "registry.k8s.io/pause:3.10"\n',
    )
    r.exec("sudo systemctl restart containerd")

    r.exec("sudo apt-get update", uid=0)
    r.exec("sudo apt-get install -y apt-transport-https ca-certificates curl gpg")
    r.exec(
        "curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.32/deb/Release.key | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg"
    )
    r.exec(
        "echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.32/deb/ /' | sudo tee /etc/apt/sources.list.d/kubernetes.list"
    )
    r.exec("sudo apt-get update", uid=1)
    r.exec(
        f"sudo apt-get install -y kubelet={version} kubeadm={version} kubectl={version}"
    )
    r.exec("sudo apt-mark hold kubelet kubeadm kubectl")

    r.replace(
        "/etc/default/kubelet",
        "KUBELET_EXTRA_ARGS=",
        'KUBELET_EXTRA_ARGS="--cgroup-driver=systemd"',
    )
    r.exec("sudo systemctl enable kubelet")


def install_minikube():
    r.exec("""curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube_latest_amd64.deb
sudo dpkg -i minikube_latest_amd64.deb""")
    r.exec("minikube start")
    r.exec("minikube delete")


def install_kube_master(master_ip: str, master_name: str):
    # init kube master
    # r.exec('sudo kubeadm config print init-defaults > kubeadm-config.yaml')
    pod_subnet = "10.244.0.0/16"
    kubeadm_config = (Settings.resources_dir / "kubeadm-config.yaml").read_text(
        encoding="utf-8"
    )
    kubeadm_config = kubeadm_config.format(
        master_ip=master_ip,
        master_name=master_name,
        pod_subnet=f"podSubnet: {pod_subnet}",
    )
    (Path.cwd() / "kubeadm-config.yaml").write_text(kubeadm_config, encoding="utf-8")
    r.exec("""sudo kubeadm config images list
sudo kubeadm config images pull""")
    r.exec("sudo kubeadm init --config kubeadm-config.yaml --upload-certs --v=9")
    r.exec("""mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config""")
    # install calico
    r.exec(
        "kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/v3.29.2/manifests/tigera-operator.yaml"
    )
    calico_config = (Settings.resources_dir / "custom-resources.yaml").read_text(
        encoding="utf-8"
    )
    calico_config = calico_config.format(pod_subnet=pod_subnet)
    (Path.cwd() / "custom-resources.yaml").write_text(calico_config, encoding="utf-8")
    r.exec("kubectl create -f custom-resources.yaml")
    while True:
        info = r.capture("kubectl get pods -n calico-system").stdout
        if (
            "Pending" not in info
            and "PodInitializing" not in info
            and "Init" not in info
            and "ContainerCreating" not in info
        ):
            break
