// A small OpenAPI 3 spec used by the "Load sample" button so the whole flow
// can be demoed in seconds without hunting down a real spec.
export const SAMPLE_SPEC = JSON.stringify(
  {
    openapi: "3.0.0",
    info: { title: "Swagger Petstore", version: "1.0.0" },
    servers: [{ url: "https://petstore3.swagger.io/api/v3" }],
    components: {
      securitySchemes: {
        ApiKeyAuth: { type: "apiKey", in: "header", name: "api_key" },
      },
    },
    paths: {
      "/pet/findByStatus": {
        get: {
          operationId: "findPetsByStatus",
          summary: "Finds pets by status",
          parameters: [
            {
              name: "status",
              in: "query",
              required: false,
              schema: { type: "string" },
              description: "Status values: available, pending, sold",
            },
          ],
        },
      },
      "/pet/{petId}": {
        get: {
          operationId: "getPetById",
          summary: "Find pet by ID",
          parameters: [
            {
              name: "petId",
              in: "path",
              required: true,
              schema: { type: "integer" },
            },
          ],
        },
        delete: {
          operationId: "deletePet",
          summary: "Deletes a pet",
          parameters: [
            {
              name: "petId",
              in: "path",
              required: true,
              schema: { type: "integer" },
            },
          ],
        },
      },
      "/pet": {
        post: {
          operationId: "addPet",
          summary: "Add a new pet to the store",
          requestBody: {
            required: true,
            content: {
              "application/json": {
                schema: {
                  type: "object",
                  properties: {
                    name: { type: "string" },
                    status: { type: "string" },
                  },
                },
              },
            },
          },
        },
      },
    },
  },
  null,
  2
);
