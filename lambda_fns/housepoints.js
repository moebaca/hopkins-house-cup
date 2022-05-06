
exports.handler = async (event) => {
  let data = {
    hufflepuff: 20,
    slytherin: 10,
    gryffindor: 40,
    ravenclaw: 80
  };
  let res =  {
    statusCode: 200,
    headers: { 
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*' 
    },
    body: JSON.stringify(data)
  };
  return res;
};