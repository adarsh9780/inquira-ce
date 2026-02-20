export default {
    inquira: {
        output: {
            mode: 'single',
            target: './src/services/generatedApi.ts',
            client: 'axios',
            mock: false,
        },
        input: {
            target: 'http://localhost:8000/openapi.json',
        },
    },
};
