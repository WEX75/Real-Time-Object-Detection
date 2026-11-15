# ADR 002: Gestionarea stării și desenarea interactivă pe frontend

**Data:** 02 Noiembrie 2026
**Status:** Acceptat

## Context
Modulul de frontend trebuie să permită utilizatorului definirea vizuală a zonelor de interes direct pe fluxul video și asocierea acestora cu reguli specifice. Aveam nevoie de o soluție performantă pentru manipularea graficii 2D și de o metodă eficientă pentru a transfera datele asincrone (coordonate, nume zone, reguli active) între componenta video și panoul de control.

## Decizie
Am optat pentru utilizarea următoarelor librării în ecosistemul React:
1. **React Konva:** Pentru manipularea elementului HTML5 `<canvas>`. Permite desenarea declarativă a poligoanelor (dreptunghiuri prin drag & drop cu `onMouseMove`), extrăgând direct sistemul de coordonate necesar pentru modulul Vision.
2. **Zustand:** Pentru managementul stării globale. Crearea unui "store" centralizat previne propagarea complexă a datelor (prop drilling) și decuplează memoria aplicației de ciclul de randare vizuală.

## Consecințe
* **Pozitive:** Viteză crescută de dezvoltare, performanță optimă la desenarea interactivă și izolare logică între sistemul video și editorul de formulare.
* **Negative/Limitări:** Integrarea `react-konva` necesită o aliniere strictă a versiunilor, forțând utilizarea pachetului compatibil cu React 18 prin parametrul NPM `--legacy-peer-deps`.