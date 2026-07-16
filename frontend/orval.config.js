export default {
    inquira: {
        output: {
            mode: 'single',
            target: './src/services/generatedApi.ts',
            client: 'axios',
            mock: false,
        },
        input: {
            target: './openapi.json',
        },
    },
};
