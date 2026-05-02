function trigger(cond) {
    {
        target: switch (1) {
            case 1:
                do {
                    if (cond) break target;
                } while ((x = 1) && false);
                break;
            default:
                x = 1;
        }
        // %DebugPrint(x);
        print(x);   // crash here due to seeing a hole
        let x;
    }
}
trigger(true);
