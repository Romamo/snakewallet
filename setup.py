from setuptools import setup, find_packages

setup(
    name='snakewallet',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        'hexbytes',
        'eth_typing',
        'qrcode',
        'tronscan @ git+https://github.com/Romamo/tronscan#egg=tronscan',
        'itrx @ git+https://github.com/Romamo/itrx#egg=itrx'
    ],
    extras_require={
        'solana': [
            'git+https://github.com/michaelhly/solana-py#egg=solana',
            'solders'
        ],
        'ethereum': [
            'web3',
        ],
        'tron': [
            'tronpy',
        ]
    },
    author='Roman Medvedev',
    author_email='github@romavm.dev',
    description='A client for interacting with the Tronscan API',
    url='https://github.com/Romamo/tronscan',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.10',
)