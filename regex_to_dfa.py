from collections import defaultdict, deque
from dataclasses import dataclass


# Guarda el inicio y fin de un fragmento del NFA
@dataclass
class NFAFragment:
    start: int
    accept: int


# Genera estados consecutivos 0, 1, 2, 3...
class StateGenerator:
    def __init__(self):
        self.current = 0

    # Regresa un nuevo estado y avanza el contador
    def new_state(self) -> int:
        state = self.current
        self.current += 1
        return state


# Representa un NFA con epsilon
class NFA:
    EPSILON = '#'

    def __init__(self):
        self.transitions = defaultdict(list)
        self.start_state = None
        self.accept_state = None
        self.states = set()

    # Agrega una transicion al NFA
    def add_transition(self, source: int, target: int, symbol: str):
        self.transitions[source].append((target, symbol))
        self.states.add(source)
        self.states.add(target)

    # Define el estado inicial y final del NFA
    def set_start_accept(self, start: int, accept: int):
        self.start_state = start
        self.accept_state = accept
        self.states.add(start)
        self.states.add(accept)


# Representa un DFA
class DFA:
    def __init__(self):
        self.transitions = {}
        self.start_state = None
        self.accept_states = set()
        self.states = set()


# Revisa si un caracter pertenece al alfabeto
def is_symbol(char: str, alphabet: set) -> bool:
    return char in alphabet


# Convierte una regex infija a postfix usando precedencia
def infix_to_postfix(regex: str, alphabet: set) -> str:
    precedence = {
        '|': 1,
        '.': 2,
        '*': 3
    }

    output = []
    operators = []

    # Recorre cada caracter de la regex
    for char in regex:
        # Si es simbolo del alfabeto se manda a salida
        if is_symbol(char, alphabet):
            output.append(char)

        # Si abre parentesis se guarda en operadores
        elif char == '(':
            operators.append(char)

        # Si cierra parentesis se vacia hasta encontrar '('
        elif char == ')':
            while operators and operators[-1] != '(':
                output.append(operators.pop())

            # Si no hay '(' la regex esta mal
            if not operators:
                raise ValueError("Error: parentesis desbalanceados en la expresion regular.")

            operators.pop()

        # Si es operador se compara precedencia
        elif char in precedence:
            while (
                operators and
                operators[-1] != '(' and
                precedence.get(operators[-1], 0) >= precedence[char]
            ):
                output.append(operators.pop())

            operators.append(char)

        # Si aparece algo raro se marca error
        else:
            raise ValueError(f"Error: caracter no valido en la regex: '{char}'")

    # Saca operadores restantes al final
    while operators:
        if operators[-1] in '()':
            raise ValueError("Error: parentesis desbalanceados en la expresion regular.")
        output.append(operators.pop())

    return ''.join(output)


# Construye un NFA desde una regex postfix con Thompson
def postfix_to_nfa(postfix: str, alphabet: set) -> NFA:
    generator = StateGenerator()
    nfa = NFA()
    stack = []

    # Recorre cada simbolo de la postfix
    for char in postfix:
        # Si es simbolo se crea un fragmento basico
        if is_symbol(char, alphabet):
            start = generator.new_state()
            accept = generator.new_state()
            nfa.add_transition(start, accept, char)
            stack.append(NFAFragment(start, accept))

        # Si es concatenacion une dos fragmentos
        elif char == '.':
            if len(stack) < 2:
                raise ValueError("Error: faltan operandos para el operador de concatenacion '.'")

            fragment2 = stack.pop()
            fragment1 = stack.pop()

            nfa.add_transition(fragment1.accept, fragment2.start, NFA.EPSILON)
            stack.append(NFAFragment(fragment1.start, fragment2.accept))

        # Si es union crea nuevo inicio y nuevo final
        elif char == '|':
            if len(stack) < 2:
                raise ValueError("Error: faltan operandos para el operador de union '|'")

            fragment2 = stack.pop()
            fragment1 = stack.pop()

            start = generator.new_state()
            accept = generator.new_state()

            nfa.add_transition(start, fragment1.start, NFA.EPSILON)
            nfa.add_transition(start, fragment2.start, NFA.EPSILON)
            nfa.add_transition(fragment1.accept, accept, NFA.EPSILON)
            nfa.add_transition(fragment2.accept, accept, NFA.EPSILON)

            stack.append(NFAFragment(start, accept))

        # Si es estrella crea los bucles epsilon
        elif char == '*':
            if len(stack) < 1:
                raise ValueError("Error: falta operando para el operador '*'")

            fragment = stack.pop()

            start = generator.new_state()
            accept = generator.new_state()

            nfa.add_transition(start, fragment.start, NFA.EPSILON)
            nfa.add_transition(start, accept, NFA.EPSILON)
            nfa.add_transition(fragment.accept, fragment.start, NFA.EPSILON)
            nfa.add_transition(fragment.accept, accept, NFA.EPSILON)

            stack.append(NFAFragment(start, accept))

        # Si no es nada valido se marca error
        else:
            raise ValueError(f"Error: simbolo inesperado en postfix: '{char}'")

    # Al final solo debe quedar un fragmento final
    if len(stack) != 1:
        raise ValueError("Error: la expresion regular es invalida.")

    final_fragment = stack.pop()
    nfa.set_start_accept(final_fragment.start, final_fragment.accept)

    return nfa


# Calcula la epsilon cerradura de un conjunto de estados
def epsilon_closure(nfa: NFA, states: set) -> frozenset:
    closure = set(states)
    changed = True

    # Repite mientras sigan apareciendo estados nuevos
    while changed:
        changed = False
        new_states = set()

        # Revisa cada estado actual de la cerradura
        for state in closure:
            for target, symbol in nfa.transitions.get(state, []):
                # Si la transicion es epsilon y no estaba se agrega
                if symbol == NFA.EPSILON and target not in closure:
                    new_states.add(target)

        # Si hubo nuevos estados se actualiza la cerradura
        if new_states:
            closure.update(new_states)
            changed = True

    return frozenset(closure)


# Hace move desde un conjunto de estados con un simbolo
def move(nfa: NFA, states: set, symbol: str) -> set:
    result = set()

    # Revisa cada estado y sus transiciones
    for state in states:
        for target, transition_symbol in nfa.transitions.get(state, []):
            # Si el simbolo coincide se agrega el destino
            if transition_symbol == symbol:
                result.add(target)

    return result


# Convierte 0 en A, 1 en B, 26 en AA, etc
def state_name(index: int) -> str:
    name = ""
    index += 1

    # Arma el nombre letra por letra
    while index > 0:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name

    return name


# Convierte un NFA con epsilon a DFA por subconjuntos
def nfa_to_dfa(nfa: NFA, alphabet: set) -> tuple[DFA, dict]:
    dfa = DFA()

    # El inicio del DFA es la epsilon cerradura del inicio del NFA
    start_subset = epsilon_closure(nfa, {nfa.start_state})

    subset_to_name = {start_subset: state_name(0)}
    name_to_subset = {state_name(0): start_subset}

    queue = deque([start_subset])

    dfa.start_state = subset_to_name[start_subset]
    dfa.states.add(dfa.start_state)
    dfa.transitions[dfa.start_state] = {}

    # Si el subset tiene el final del NFA, es final en el DFA
    if nfa.accept_state in start_subset:
        dfa.accept_states.add(dfa.start_state)

    next_index = 1

    # Recorre todos los subsets pendientes
    while queue:
        current_subset = queue.popleft()
        current_name = subset_to_name[current_subset]

        if current_name not in dfa.transitions:
            dfa.transitions[current_name] = {}

        # Calcula transiciones del DFA para cada simbolo
        for symbol in sorted(alphabet):
            moved = move(nfa, current_subset, symbol)
            closure = epsilon_closure(nfa, moved)

            # Si no se llega a nada con ese simbolo se ignora
            if not closure:
                continue

            # Si el subset es nuevo se crea un nuevo estado del DFA
            if closure not in subset_to_name:
                new_name = state_name(next_index)
                next_index += 1

                subset_to_name[closure] = new_name
                name_to_subset[new_name] = closure
                queue.append(closure)

                dfa.states.add(new_name)
                dfa.transitions[new_name] = {}

                # Si el subset contiene el final del NFA se marca final
                if nfa.accept_state in closure:
                    dfa.accept_states.add(new_name)

            dfa.transitions[current_name][symbol] = subset_to_name[closure]

    return dfa, name_to_subset


# Imprime el NFA en formato sencillo
def print_nfa(nfa: NFA):
    print("\nNFA:\n")

    # Recorre estados en orden para mostrar transiciones
    for state in sorted(nfa.states):
        transitions = nfa.transitions.get(state, [])
        if transitions:
            formatted = ", ".join(f"({target}, '{symbol}')" for target, symbol in transitions)
            print(f"{state} => [{formatted}]")

    print(f"\nAccepting state: {nfa.accept_state}")


# Imprime el DFA en formato sencillo
def print_dfa(dfa: DFA):
    print("\nDFA:\n")

    # Recorre estados del DFA y muestra transiciones
    for state in sorted(dfa.states):
        transitions = dfa.transitions.get(state, {})
        if transitions:
            formatted = ", ".join(
                f"('{target}', '{symbol}')"
                for symbol, target in sorted(transitions.items())
            )
            print(f"{state} => [{formatted}]")

    print(f"\nAccepting states: {sorted(dfa.accept_states)}")


# Muestra la entrada y la postfix generada
def print_internal_info(regex: str, postfix: str):
    print("\n----RESULTS----\n")
    print("INPUT:\n")
    print(regex)
    print("\nRegex en postfix:")
    print(postfix)


# Valida que el alfabeto no este vacio ni use simbolos reservados
def validate_alphabet(alphabet_string: str) -> set:
    if not alphabet_string:
        raise ValueError("Error: el alfabeto no puede estar vacio.")

    alphabet = set(alphabet_string)

    reserved = {'|', '.', '*', '(', ')', '#'}
    invalid = alphabet.intersection(reserved)

    # Si hay caracteres reservados se marca error
    if invalid:
        raise ValueError(
            f"Error: el alfabeto contiene caracteres reservados no permitidos: {invalid}"
        )

    return alphabet


# Valida que la regex use simbolos permitidos y punto explicito
def validate_regex(regex: str, alphabet: set):
    if not regex:
        raise ValueError("Error: la expresion regular no puede estar vacia.")

    allowed = set(alphabet) | {'|', '.', '*', '(', ')'}


    # Revisa que todos los caracteres sean validos
    for char in regex:
        if char not in allowed:
            raise ValueError(f"Error: caracter no permitido en la regex: '{char}'")

    # Revisa casos donde falte el punto de concatenacion
    for i in range(len(regex) - 1):
        current_char = regex[i]
        next_char = regex[i + 1]

        current_is_symbol = current_char in alphabet
        next_is_symbol = next_char in alphabet

        # Dos simbolos seguidos sin punto
        if current_is_symbol and next_is_symbol:
            raise ValueError(
                "Error: la concatenacion debe escribirse explicitamente con '.'. Ejemplo correcto: a.b"
            )

        # Simbolo antes de parentesis sin punto
        if current_is_symbol and next_char == '(':
            raise ValueError(
                "Error: falta '.' antes de '('. Ejemplo correcto: a.(b|c)"
            )

        # Parentesis antes de simbolo sin punto
        if current_char == ')' and next_is_symbol:
            raise ValueError(
                "Error: falta '.' despues de ')'. Ejemplo correcto: (a|b).a"
            )

        # Parentesis juntos sin punto
        if current_char == ')' and next_char == '(':
            raise ValueError(
                "Error: falta '.' entre ')' y '('. Ejemplo correcto: (a|b).(a|b)"
            )

        # Estrella antes de simbolo sin punto
        if current_char == '*' and next_is_symbol:
            raise ValueError(
                "Error: falta '.' despues de '*'. Ejemplo correcto: a*.b"
            )

        # Estrella antes de parentesis sin punto
        if current_char == '*' and next_char == '(':
            raise ValueError(
                "Error: falta '.' despues de '*'. Ejemplo correcto: (a|b)*.(a|b)"
            )


# Funcion principal del programa
def main():
    print("Proyecto 1 Conversor de RegEx -> NFA -> DFA")
    print("Cesar Augusto Ramirez Davila A01712439")
    print("Operadores usables: |  .  *  ()")
    print("La concatenacion debe escribirse explicitamente con '.'")
    print("Ejemplo de expresion regular: (a|b)*.a.b.b")
    print("Ejemplo de alfabeto para la expresion regular: ab")

    alphabet_input = input("Ingresa el alfabeto: ").strip()
    regex_input = input("Ingresa la expresion regular: ").strip()

    alphabet = validate_alphabet(alphabet_input)
    validate_regex(regex_input, alphabet)

    # Convierte la regex a postfix
    postfix = infix_to_postfix(regex_input, alphabet)

    # Construye el NFA con el algoritmo de Thompson
    nfa = postfix_to_nfa(postfix, alphabet)

    # Convierte el NFA a DFA
    dfa, _ = nfa_to_dfa(nfa, alphabet)

    # Muestra los resultados y cambios de estado
    print_internal_info(regex_input, postfix)
    print_nfa(nfa)
    print_dfa(dfa)


# Punto de entrada del programa
if __name__ == "__main__":
    main()