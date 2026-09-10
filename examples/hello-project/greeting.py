def greet(name: str = 'ROVNY') -> str:
    # Docstring explaining the greet function
    return f'Hello, {name}!'


if __name__ == '__main__':
    print(greet())