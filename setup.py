from setuptools import setup, find_packages

setup(
        name="cococount",
        version="0.1",
        packages=[
                "cococount",
                "cococount.static"],
        scripts=["bin/cococount-server"],
        install_requires=["aiohttp>=1.3.0", "beancount>=2.0rc1", "systemd"],
        package_data = {"cococount.static" : ["*.html", "css/*.css", "css/*.ttf"]}
        )
